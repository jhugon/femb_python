//compile independently with: g++ -std=c++11 -o processNtuple_gainMeasurement processNtuple_gainMeasurement.cxx `root-config --cflags --glibs`
#include <iostream>
#include <fstream>
#include <sstream>
#include <cstdlib>
using namespace std;

#include "TROOT.h"
#include "TMath.h"
#include "TApplication.h"
#include "TFile.h"
#include "TTree.h"
#include "TH1.h"
#include "TH2.h"
#include "TString.h"
#include "TCanvas.h"
#include "TSystem.h"
#include "TGraph.h"
#include "TProfile2D.h"
#include "TF1.h"
#include "TLegend.h"
#include "TImage.h"

using namespace std;

//global TApplication object declared here for simplicity
TApplication *theApp;

class Analyze {
	public:
	Analyze(std::string inputFileName);
        int processFileName(std::string inputFileName, std::string &baseFileName);
	void doAnalysis();
	void organizeData();
	void analyzeSubrun(unsigned int subrun);
	void analyzeChannel(unsigned int chan, const std::vector<unsigned short> &wf);
	void drawWf(unsigned int chan, const std::vector<unsigned short> &wf);
	void findPulses(const std::vector<unsigned short> &wf);
	void analyzePulse(unsigned int subrun, unsigned int chan,  int startSampleNum, const std::vector<unsigned short> &wf);
	void measurePulseHeights(unsigned int subrun, unsigned int chan);
	void measureGain();
        void outputResults();

	//Files
	TFile* inputFile;
	TFile *gOut;

	//ROI tr_rawdata variables
	TTree *tr_rawdata;
	unsigned short subrunIn, chanIn;
	std::vector<unsigned short> *wfIn = 0;

	//Constants
	const int numChan = 128;// 35t
	const float SAMP_PERIOD = 0.5; //us
	const int numSubrun = 64;
	const int numConfig = 1;
	const int numSignalSize = 64;
	const int preRange = 20;
	const int postRange = 20;

	//data objects
	TCanvas* c0;
	TGraph *gCh;
        std::vector<unsigned short> wfAll[64][128];

	//histograms
	TH2F *hSampVsChan;
	TProfile *pSampVsChan;
	TH2F *hMeanVsChan;
	TProfile *pMeanVsChan;
	TH2F *hRmsVsChan;
	TProfile *pRmsVsChan;
	TProfile *pFracStuckVsChan;
	TProfile2D *pFFTVsChan;

	//Pulse height measurement	
	std::vector<int> pulseStart;
	TH1F *hPulseHeights;

	//Gain Measurement
	TGraph *gPulseVsSignal[128];
	TH2F *hPulseVsSignal[128];
	double signalSizes[64] = {0.606,0.625,0.644,0.663,0.682,0.701,0.720,0.739,0.758,0.777,0.796,0.815,0.834,
		0.853,0.872,0.891,0.909,0.928,0.947,0.966,0.985,1.004,1.023,1.042,1.061,1.080,1.099,1.118,1.137,
		1.156,1.175,1.194,1.213,1.232,1.251,1.269,1.288,1.307,1.326,1.345,1.364,1.383,1.402,1.421,1.440,
		1.459,1.478, 1.497,1.516,1.535,1.554,1.573,1.592,1.611,1.629,1.648,1.667,1.686,1.705,1.724,1.743,
		1.762,1.781,1.800};

	TH1F *hGainVsChan;
	TH1F *hEncVsChan;
	TH1F *hGain;
	TH1F *hEnc;
};

Analyze::Analyze(std::string inputFileName){

	//get input file
	if( inputFileName.empty() ){
		std::cout << "Error invalid file name" << std::endl;
		gSystem->Exit(0);
	}

	inputFile = new TFile(inputFileName.c_str());
	if (inputFile->IsZombie()) {
		std::cout << "Error opening input file" << std::endl;
		gSystem->Exit(0);
	}

	if( !inputFile ){
		std::cout << "Error opening input file" << std::endl;
		gSystem->Exit(0);
	}

	//initialize tr_rawdata branches
  	tr_rawdata = (TTree*) inputFile->Get("femb_wfdata");
  	if( !tr_rawdata ){
		std::cout << "Error opening input file tree" << std::endl;
		gSystem->Exit(0);
  	}
	tr_rawdata->SetBranchAddress("subrun", &subrunIn);
	tr_rawdata->SetBranchAddress("chan", &chanIn);
  	tr_rawdata->SetBranchAddress("wf", &wfIn);

	//make output file
  	std::string outputFileName = "output_processNtuple_gainMeasurement.root";
	//if( processFileName( inputFileName, outputFileName ) )
	//	outputFileName = "output_processNtuple_gainMeasurement_" + outputFileName;

  	gOut = new TFile(outputFileName.c_str() , "RECREATE");

  	//initialize canvas
  	c0 = new TCanvas("c0", "c0",1400,800);

	//initialize graphs
	gCh = new TGraph();

  	//output histograms, data objects
  	hSampVsChan = new TH2F("hSampVsChan","",numChan,0-0.5,numChan-0.5,4096,-0.5,4096-0.5);
 	pSampVsChan = new TProfile("pSampVsChan","",numChan,0-0.5,numChan-0.5);
  	hMeanVsChan = new TH2F("hMeanVsChan","",numChan,0-0.5,numChan-0.5,4096,-0.5,4096-0.5);
	pMeanVsChan = new TProfile("pMeanVsChan","",numChan,0-0.5,numChan-0.5);
  	hRmsVsChan = new TH2F("hRmsVsChan","",numChan,0-0.5,numChan-0.5,300,0,300.);
  	pRmsVsChan = new TProfile("pRmsVsChan","",numChan,0-0.5,numChan-0.5);
	pFracStuckVsChan = new TProfile("pFracStuckVsChan","",numChan,0-0.5,numChan-0.5);
	pFFTVsChan = new TProfile2D("pFFTVsChan","",numChan,0-0.5,numChan-0.5,100,0,1);

	//gain measurement objects
	hPulseHeights = new TH1F("hPulseHeights","",4100,0-0.5,4100-0.5);
	for(int ch = 0 ; ch < numChan ; ch++ ){
		gPulseVsSignal[ch] = new TGraph();

		char name[200];
		memset(name,0,sizeof(char)*100 );
        	sprintf(name,"hPulseVsSignal_ch_%i",ch);
		hPulseVsSignal[ch] = new TH2F(name,"",numSubrun, 0-0.5,numSubrun,400,0,4000);
	}

	hGain = new TH1F("hGain","",500,0,5000);
	hEnc = new TH1F("hEnc","",200,0,2000);

	hGainVsChan = new TH1F("hGainVsChan","",numChan,0-0.5,numChan-0.5);
	hEncVsChan = new TH1F("hEncVsChan","",numChan,0-0.5,numChan-0.5);
}

int Analyze::processFileName(std::string inputFileName, std::string &baseFileName){
        //check if filename is empty
        if( inputFileName.size() == 0 ){
                std::cout << "processFileName : Invalid filename " << std::endl;
                return 0;
        }

        //remove path from name
        size_t pos = 0;
        std::string delimiter = "/";
        while ((pos = inputFileName.find(delimiter)) != std::string::npos)
                inputFileName.erase(0, pos + delimiter.length());

	if( inputFileName.size() == 0 ){
                std::cout << "processFileName : Invalid filename " << std::endl;
                return 0;
        }

        //replace / with _
        std::replace( inputFileName.begin(), inputFileName.end(), '/', '_'); // replace all 'x' to 'y'
        std::replace( inputFileName.begin(), inputFileName.end(), '-', '_'); // replace all 'x' to 'y'
	baseFileName = inputFileName;
	
	return 1;
}

void Analyze::doAnalysis(){
	//organize tree data by subrun
	std::cout << "Organizing data by subrun" << std::endl;
	organizeData();

	//analyze each subrun individually
	for(unsigned int sr = 0 ; sr < numSubrun ; sr++){
		std::cout << "Analyzing subrun " << sr << std::endl;
		analyzeSubrun(sr);
	}

	//do summary analyses
	std::cout << "Doing summary analysis" << std::endl;
	measureGain();

	outputResults();
}

void Analyze::outputResults(){

	pMeanVsChan->SetStats(kFALSE);
	pMeanVsChan->GetXaxis()->SetTitle("FEMB Channel #");
	pMeanVsChan->GetYaxis()->SetTitle("Pedestal Mean (ADC counts)");

	pFFTVsChan->SetStats(kFALSE);
	pFFTVsChan->GetXaxis()->SetTitle("FEMB Channel #");
	pFFTVsChan->GetYaxis()->SetTitle("Frequency (MHz)");

	hGainVsChan->SetStats(kFALSE);
	hGainVsChan->GetXaxis()->SetTitle("FEMB Channel #");
	hGainVsChan->GetYaxis()->SetTitle("Gain (e- / ADC count)");

	hEncVsChan->SetStats(kFALSE);
	hEncVsChan->GetXaxis()->SetTitle("FEMB Channel #");
	hEncVsChan->GetYaxis()->SetTitle("ENC (e-)");

	//hGain->SetStats(kFALSE);
        hGain->GetXaxis()->SetRangeUser(0,1000);
	hGain->GetXaxis()->SetTitle("Gain (e- / ADC count)");
	hGain->GetYaxis()->SetTitle("# of Channels");

	//hEnc->SetStats(kFALSE);
	hEnc->GetXaxis()->SetTitle("ENC (e-)");
	hEnc->GetYaxis()->SetTitle("# of Channels");

	//make summary plot
	c0->Clear();
	c0->Divide(2,3);
	
	c0->cd(1);
	pMeanVsChan->Draw();
	
	c0->cd(2);
	pFFTVsChan->Draw("COLZ");
	
	c0->cd(3);
	hGainVsChan->Draw();

	c0->cd(4);
	hEncVsChan->Draw();

        c0->cd(5);
	hGain->Draw();
	  
	c0->cd(6);
	hEnc->Draw();

	

	c0->Update();

	//save summary plots
	TImage *img = TImage::Create();
	img->FromPad(c0);
  	std::stringstream imgstream;
	imgstream << "summaryPlot_gainMeasurement.png";
	std::string imgstring( imgstream.str() );
  	img->WriteImage(imgstring.c_str());

  	//output histograms, data objects
 	gOut->Cd("");
	c0->Write("c0_SummaryPlot");
  	hSampVsChan->Write();
	pSampVsChan->Write();
  	hMeanVsChan->Write();
	pMeanVsChan->Write();

	hRmsVsChan->GetXaxis()->SetTitle("Channel #");
	hRmsVsChan->GetYaxis()->SetTitle("Pedestal RMS (ADC counts)");
  	hRmsVsChan->Write();

  	pRmsVsChan->Write();
	pFracStuckVsChan->Write();
	pFFTVsChan->Write();

	hGainVsChan->GetXaxis()->SetTitle("Channel #");
	hGainVsChan->GetYaxis()->SetTitle("Gain (e- / ADC count)");
	hGainVsChan->Write();

	hEncVsChan->GetXaxis()->SetTitle("Channel #");
	hEncVsChan->GetYaxis()->SetTitle("ENC (e-)");
	hEncVsChan->Write();

	hGain->GetXaxis()->SetTitle("Gain (e- / ADC count)");
	hGain->GetYaxis()->SetTitle("# of Channels");
	hGain->Write();

	hEnc->GetXaxis()->SetTitle("ENC (e-)");
	hEnc->GetYaxis()->SetTitle("# of Channels");
	hEnc->Write();

	for(int ch = 0 ; ch < numChan ; ch++ ){
		std::string title = "gPulseHeightVsSignal_Ch_" + to_string( ch );
		gPulseVsSignal[ch]->GetXaxis()->SetTitle("Number of Electrons (e-)");
		gPulseVsSignal[ch]->GetYaxis()->SetTitle("Measured Pulse Height (ADC counts)");
		gPulseVsSignal[ch]->Write(title.c_str());
	}

	//write subrun specific objects
  	gOut->Close();
}

void Analyze::organizeData(){
	//loop over tr_rawdata entries
  	Long64_t nEntries(tr_rawdata->GetEntries());
	tr_rawdata->GetEntry(0);
	//loop over input waveforms, group waveforms by subrun
	for(Long64_t entry(0); entry<nEntries; ++entry) { 
		tr_rawdata->GetEntry(entry);

		//make sure channels and subrun values are ok
		if( subrunIn < 0 || subrunIn >= numSubrun ) continue;
		if( chanIn < 0 || chanIn >= numChan ) continue;
		
		for( unsigned int s = 0 ; s < wfIn->size() ; s++ )
			wfAll[subrunIn][chanIn].push_back( wfIn->at(s) );
  	}//entries
}

void Analyze::analyzeSubrun(unsigned int subrun){

	//reset plots

	//loop over channels, update subrun specific plots
	for(unsigned int ch = 0 ; ch < numChan ; ch++){
		if( subrun == 0 ){
			analyzeChannel(ch,wfAll[subrun][ch]);
			continue;
		}

		//find pulses
		findPulses(wfAll[subrun][ch]);

		//skip very noisy channels
		if( pulseStart.size() > 200 )
			continue;

		//analyze channel pulses, measure heights
		hPulseHeights->Reset();
		for( unsigned int p = 0 ; p < pulseStart.size() ; p++ )
			analyzePulse( subrun, ch, pulseStart.at(p) , wfAll[subrun][ch] ) ;

		//drawWf(ch,wfAll[subrun][ch]);
		measurePulseHeights(subrun, ch);
	}

	//put result in subrun specific object
}


//draw waveform if wanted
void Analyze::drawWf(unsigned int chan, const std::vector<unsigned short> &wf){
	gCh->Set(0);
	for( int s = 0 ; s < wf.size() ; s++ )
		gCh->SetPoint(gCh->GetN() , gCh->GetN() , wf.at(s) );
	std::cout << "Channel " << chan << std::endl;
	
	c0->Clear();
	std::string title = "Channel " + to_string( chan );
	gCh->SetTitle( title.c_str() );
	gCh->GetXaxis()->SetTitle("Sample Number");
	gCh->GetYaxis()->SetTitle("Sample Value (ADC counts)");
	gCh->Draw("ALP");
	c0->Update();
	//char ct;
	//std::cin >> ct;
	usleep(1000);
}

void Analyze::analyzeChannel(unsigned int chan, const std::vector<unsigned short> &wf){
	if( wf.size() == 0 )
		return;

	//calculate mean
	double mean = 0;
	int count = 0;
	for( int s = 0 ; s < wf.size() ; s++ ){
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);
		mean += value;
		count++;
	}
	if( count > 0 )
		mean = mean / (double) count;

	//calculate rms
	double rms = 0;
	count = 0;
	for( int s = 0 ; s < wf.size() ; s++ ){
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);
		rms += (value-mean)*(value-mean);
		count++;
	}	
	if( count > 1 )
		rms = TMath::Sqrt( rms / (double)( count - 1 ) );
	
	//fill channel waveform hists
	for( int s = 0 ; s < wf.size() ; s++ ){
		unsigned short samp =  wf.at(s);
		hSampVsChan->Fill( chan, samp);

		//measure stuck code fraction
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F )
			pFracStuckVsChan->Fill(chan, 1);
		else
			pFracStuckVsChan->Fill(chan, 0);
	}

	hMeanVsChan->Fill( chan, mean );
	pMeanVsChan->Fill( chan, mean );
	hRmsVsChan->Fill(chan, rms);
	pRmsVsChan->Fill(chan, rms);

	//load hits into TGraph, skip stuck codes
	gCh->Set(0);
	for( int s = 0 ; s < wf.size() ; s++ ){
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		gCh->SetPoint(gCh->GetN() , s , wf.at(s) );
	}

	//compute FFT - use TGraph to interpolate between missing samples
	//int numFftBins = wf.size();
	int numFftBins = 5000;
	if( numFftBins > wf.size() )
		numFftBins = wf.size();
	TH1F *hData = new TH1F("hData","",numFftBins,0,numFftBins);
	for( int s = 0 ; s < numFftBins ; s++ ){
		double adc = gCh->Eval(s);
		hData->SetBinContent(s+1,adc);
	}

	TH1F *hFftData = new TH1F("hFftData","",numFftBins,0,numFftBins);
    	hData->FFT(hFftData,"MAG");
    	for(int i = 1 ; i < hFftData->GetNbinsX() ; i++ ){
		double freq = 2.* i / (double) hFftData->GetNbinsX() ;
		pFFTVsChan->Fill( chan, freq,  hFftData->GetBinContent(i+1) );
	}

	delete hData;
	delete hFftData;
}

void Analyze::findPulses(const std::vector<unsigned short> &wf){
	if( wf.size() == 0 )
		return;

	//calculate mean
	double mean = 0;
	int count = 0;
	for( int s = 0 ; s < wf.size() ; s++ ){
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);
		mean += value;
		count++;
	}
	if( count > 0 )
		mean = mean / (double) count;

	//calculate rms
	double rms = 0;
	count = 0;
	for( int s = 0 ; s < wf.size() ; s++ ){
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);
		rms += (value-mean)*(value-mean);
		count++;
	}	
	if( count > 1 )
		rms = TMath::Sqrt( rms / (double)( count - 1 ) );

	if( count == 0 )
		return;

	//calculate RMS from histogram

	//look for pulses along waveform, hardcoded number might be bad
	double threshold = 5*rms;
	if( threshold > 50 )
		threshold = 50.;
	int numPulse = 0;
	pulseStart.clear();
	for( int s = 0 + preRange ; s < wf.size() - postRange - 1 ; s++ ){
		if(  (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		if(  (wf.at(s+1) & 0x3F ) == 0x0 || (wf.at(s+1) & 0x3F ) == 0x3F ) continue;
		double value =  wf.at(s);
		double valueNext = wf.at(s+1);
		if(1 && valueNext > mean + threshold && value < mean + threshold ){
			//have pulse, find local maxima
			numPulse++;
			int start = s;
			pulseStart.push_back(start );
		}
	}
}

void Analyze::analyzePulse(unsigned int subrun, unsigned int chan, int startSampleNum, const std::vector<unsigned short> &wf){
	//require pulse is not beside waveform edge
	if( startSampleNum <= preRange || startSampleNum >= wf.size()  - postRange )
		return;

	//calculate baseline estimate in range preceeding pulse
	double mean = 0;
	int count = 0;
	for(int s = startSampleNum-20 ; s < startSampleNum - 10 ; s++){
		if( s < 0 ) continue;
		if( s >= wf.size() ) continue;
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);
		mean += value;
		count++;
	}
	if( count > 0)
		mean = mean / (double) count;
	if( count == 0 )
		return;

	//calculate baseline rms in range preceeding pulse
	double rms = 0;
	count = 0;
	for(int s = startSampleNum-20 ; s < startSampleNum - 10 ; s++){
		if( s < 0 ) continue;
		if( s >= wf.size() ) continue;
		if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);
		rms += (value - mean)*(value - mean);
		count++;
	}
	if(count - 1 > 0)
		rms = TMath::Sqrt( rms /(double)(  count - 1  ) );
	if( count == 0 )
		return;

	//find maximum sample value
	int maxSampTime = -1;
	int maxSampVal = -1;
	int maxSamp = -1;
	for(int s = startSampleNum-preRange ; s < startSampleNum + postRange ; s++){
		if( s < 0 ) continue;
		if( s >= wf.size() ) continue;
		//if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		double value = wf.at(s);

		if( s < startSampleNum - 5 ) continue;
		if( s > startSampleNum + 10 ) continue;
		if( value > maxSampVal ){
			maxSampTime = s*SAMP_PERIOD;
			maxSampVal = value;
			maxSamp = s;
		}
	}

	//load pulse into graph object, do NOT include stuck codes, convert sample number to time (us)
	gCh->Set(0);
	for(int s = startSampleNum-preRange ; s < startSampleNum + postRange ; s++){
		if( s < 0 ) continue;
		if( s >= wf.size() ) continue;
		//if( (wf.at(s) & 0x3F ) == 0x0 || (wf.at(s) & 0x3F ) == 0x3F ) continue;
		gCh->SetPoint(gCh->GetN() , s*SAMP_PERIOD , wf.at(s) );
	}

	//integrate over expected pulse range, note use of averaged waveform pulse time
	double sumVal = 0;
	for( int s = 0 ; s < gCh->GetN() ; s++ ){
		double sampTime,sampVal;
		gCh->GetPoint(s,sampTime,sampVal);
		sumVal += sampVal - mean;
	}

	//selection criteria
	

	//update histograms
	double pulseHeight = maxSampVal - mean;
	hPulseHeights->Fill(pulseHeight);
	hPulseVsSignal[chan]->Fill(subrun, pulseHeight);

	//draw waveform if needed
	if(0){
		std::cout << mean << "\t" << maxSampVal << "\t" << pulseHeight << std::endl;
		//std::string title = "Subrun " + to_string( subrun ) + " Channel " + to_string( chan ) + " Height " + to_string( int(pulseHeight) );
		std::string title = " Height " + to_string( int(pulseHeight) );
		gCh->SetTitle( title.c_str() );

		gCh->GetXaxis()->SetTitle("Sample Number");
		gCh->GetYaxis()->SetTitle("Sample Value (ADC counts)");
	
		c0->Clear();
		gCh->SetMarkerStyle(21);
		gCh->SetMarkerColor(kRed);
		gCh->Draw("ALP");
		c0->Update();
		usleep(100000);
		char ct;
		std::cin >> ct;
	}
}


void Analyze::measurePulseHeights(unsigned int subrun, unsigned int chan){

	if( hPulseHeights->GetEntries() < 10 )
		return;

	if( subrun >= numSubrun )
		return;
	
	if( chan >= numChan )
		return;

	//get average pulse height, update plots
	double mean = hPulseHeights->GetMean();
	double signalCharge = (signalSizes[subrun]-signalSizes[0])*183*6241;
	gPulseVsSignal[chan]->SetPoint( gPulseVsSignal[chan]->GetN() ,signalCharge , mean);
	
	if(0){
		std::cout << "mean " << mean << std::endl;
		std::string title = "Subrun " + to_string( subrun ) + ", Channel " + to_string( chan ) + ", e- " + to_string( int(signalCharge) ) 
			+ ", Height " + to_string( int(mean) );
		hPulseHeights->SetTitle( title.c_str() );

		double max = hPulseHeights->GetBinCenter( hPulseHeights->GetMaximumBin() ) ;

		hPulseHeights->GetXaxis()->SetRangeUser( max - 50 , max + 50 );
		hPulseHeights->GetXaxis()->SetTitle("Measured Pulse Height (ADC counts)");
		hPulseHeights->GetYaxis()->SetTitle("Number of Pulses");

		c0->Clear();
		hPulseHeights->Draw();
		c0->Update();
		usleep(100000);
		char ct;
		std::cin >> ct;
	}
	return;
}

void Analyze::measureGain(){
	for(int ch = 0 ; ch < numChan ; ch++ ){
		if( gPulseVsSignal[ch]->GetN() < 3 ) continue;

		//gPulseVsSignal[ch]->GetXaxis()->SetRangeUser(700*1000.,1400*1000.);
		gPulseVsSignal[ch]->GetXaxis()->SetRangeUser(-50*1000.,700*1000.);

		//insist pulse height = 0 for signal = 0
		gPulseVsSignal[ch]->SetPoint(gPulseVsSignal[ch]->GetN(),0,0);

		TF1 *f1 = new TF1("f1","pol1",-50*1000.,700*1000.);
		f1->SetParameter(0,0);
		f1->SetParameter(1,2/1000.);
		gPulseVsSignal[ch]->Fit("f1","QR");

		double gain_AdcPerE = f1->GetParameter(1);
		double gain_ePerAdc = 0;
		if( gain_AdcPerE > 0 )
			gain_ePerAdc = 1./ gain_AdcPerE;
		hGainVsChan->SetBinContent(ch+1, gain_ePerAdc);

		double enc = pRmsVsChan->GetBinContent(ch+1)*gain_ePerAdc;
		hEncVsChan->SetBinContent(ch+1, enc);

		hGain->Fill(gain_ePerAdc);
		hEnc->Fill(enc);
	
		if(0){
			std::cout << gain_ePerAdc << std::endl;
			std::cout<< enc << std::endl;
			c0->Clear();
			gPulseVsSignal[ch]->Draw("ALP");
			c0->Update();
			char ct;
			std::cin >> ct;
		}

		delete f1;
	}

	return;
}

void processNtuple(std::string inputFileName) {

  Analyze ana(inputFileName);
  ana.doAnalysis();

  return;
}

int main(int argc, char *argv[]){
  if(argc!=2){
    cout<<"Usage: processNtuple [inputFilename]"<<endl;
    return 0;
  }

  std::string inputFileName = argv[1];
  std::cout << "inputFileName " << inputFileName << std::endl;

  //define ROOT application object
  gROOT->SetBatch(true);
  theApp = new TApplication("App", &argc, argv);
  processNtuple(inputFileName); 

  //return 1;
  gSystem->Exit(0);
}
