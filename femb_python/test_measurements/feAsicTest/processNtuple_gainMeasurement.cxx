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

#include "FitFeElecResponse.hxx"

using namespace std;

//global TApplication object declared here for simplicity
TApplication *theApp;

class Analyze {
	public:
	Analyze(std::string inputName);

	void getInputFile();
  	void getInputTree();
        bool processFileName(std::string inputFileName, std::string &baseFileName);
	void initRootObjects();

	void doAnalysis();
	void organizeData();

	void analyzeChannel(unsigned int chan);
	void computeFft(unsigned int chan, const std::vector<unsigned short> &wf);
	void drawWf(unsigned int chan, const std::vector<unsigned short> &wf);

	void findPulses(const std::vector<unsigned short> &wf,double baseMean, double baseRms);
	void getAveragePulseHeight(const std::vector<double> &pulseHeights);
	void measureGain(unsigned int chan, double baseRms);

 	void identifyBadChannel(unsigned int chan, double baseMean, double baseRms, double gain);
	void identifyBadAsic();

        void outputResults();
        void writeToRootFile();
	void makeSummaryPlot();
	void writeToTextFile();

	//Files
	std::string inputFileName;
	TFile* inputFile;
	TFile *gOut;

	//ROOT TREE tr_rawdata variables
	TTree *tr_rawdata;
	unsigned short subrunIn, chanIn;
	std::vector<unsigned short> *wfIn = 0;

	//Constants - hardcoded for now
	const int const_numChan = 64;// 35t
	const int const_numAsic = 4;// 35t
        const int const_maxCode = 0x4000;
        const float const_maxRms = 500.; //ADC counts
	const float const_maxPulseHeight = 0x4000;
	const float const_minPulseHeightForFit = 2000;
	const float const_maxPulseHeightForFit = 8000;
	const float const_maxGain = 10000;
	const float const_maxEnc = 5000;
	const int const_numFftBins = 5000;
	const float const_samplingRate = 4.;
	const int const_numSubrun = 64;
	const int const_preRange = 15;
	const int const_postRange = 25;
	const float const_minThreshold = 250;
	const int const_minNumberPulses = 10;
	const int const_cut_numBadChannels = 0;
  	const bool const_doFits = 0;

	//data objects
	TCanvas* c0;
	TGraph *gCh, *gFit;
        std::vector<unsigned short> wfAll[64][64];

	//histograms
	TH2F *hSampVsChan;
	TProfile *pMeanVsChan;
	TProfile *pRmsVsChan;
	TProfile2D *pFFTVsChan;

	//Pulse height measurement
	std::vector<int> pulseRiseStart;
	std::vector<int> pulseFallStart;
	TH1F *hPulseHeights;
	double averagePulseHeight = -1;

	//Gain Measurement
	double signalSizes[64];
	TGraph *gPulseVsSignal[64];
	TGraph *gFitPulseVsSignal[64];
	TH1F *hGainVsChan;
	TH1F *hEncVsChan;
	TH1F *hGain;
	TH1F *hEnc;
	double measuredEnc = -1;
	double measuredGain = -1;
	FitFeElecResponse_analyzePulses ffer_analyzePulses;

	//ASIC status
	bool badChannelMask[64];
	bool badAsicMask[4];
};

Analyze::Analyze(std::string inputName){

	inputFileName = inputName;
        getInputFile();
	getInputTree();

	//make output file
  	std::string outputFileName = "output_processNtuple_gainMeasurement.root";
	//if( processFileName( inputFileName, outputFileName ) )
	//	outputFileName = "output_processNtuple_gainMeasurement_" + outputFileName;
  	gOut = new TFile(outputFileName.c_str() , "RECREATE");

	//initialize bad channel mask
	for(int ch = 0 ; ch < const_numChan ; ch++ )
		badChannelMask[ch] = 0;

	//initialize bad ASIC mask
	for(int asic = 0 ; asic < const_numAsic ; asic++ )
		badAsicMask[asic] = 0;

	//define signal sizes, should be input
	for(int sr = 0 ; sr < const_numSubrun ; sr++ ){
		signalSizes[sr] = sr*0.01875;//internal pulser, V
  		signalSizes[sr] = signalSizes[sr]*183*6241;//test capacitor, convert to e-
        }

	initRootObjects();
}

void Analyze::getInputFile(){
	//get input file
	if( inputFileName.empty() ){
		std::cout << "Error invalid file name, exiting" << std::endl;
		gSystem->Exit(0);
	}

	inputFile = new TFile(inputFileName.c_str());
	if (inputFile->IsZombie()) {
		std::cout << "Error opening input file, exiting" << std::endl;
		gSystem->Exit(0);
	}

	if( !inputFile ){
		std::cout << "Error opening input file, exiting" << std::endl;
		gSystem->Exit(0);
	}
	return;
}

void Analyze::getInputTree(){
	//initialize tr_rawdata branches
  	tr_rawdata = (TTree*) inputFile->Get("femb_wfdata");
  	if( !tr_rawdata ){
		std::cout << "Error opening input file tree, exiting" << std::endl;
		gSystem->Exit(0);
  	}
	tr_rawdata->SetBranchAddress("subrun", &subrunIn);
	tr_rawdata->SetBranchAddress("chan", &chanIn);
  	tr_rawdata->SetBranchAddress("wf", &wfIn);
}

bool Analyze::processFileName(std::string inputFileName, std::string &baseFileName){
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

void Analyze::initRootObjects(){
  	//initialize canvas
  	c0 = new TCanvas("c0", "c0",1400,800);

	//initialize graphs
	gCh = new TGraph();
	gFit = new TGraph();

  	//output histograms, data objects
  	hSampVsChan = new TH2F("hSampVsChan","",const_numChan,0-0.5,const_numChan-0.5,100,-0.5,const_maxCode-0.5);
	pMeanVsChan = new TProfile("pMeanVsChan","",const_numChan,0-0.5,const_numChan-0.5);
  	pRmsVsChan = new TProfile("pRmsVsChan","",const_numChan,0-0.5,const_numChan-0.5);
	pFFTVsChan = new TProfile2D("pFFTVsChan","",const_numChan,0-0.5,const_numChan-0.5,100,0,const_samplingRate/2.);

	//gain measurement objects
	hPulseHeights = new TH1F("hPulseHeights","",1000,0,const_maxPulseHeight);
	for(int ch = 0 ; ch < const_numChan ; ch++ ){
		gPulseVsSignal[ch] = new TGraph();
		gFitPulseVsSignal[ch] = new TGraph();
	}

	hGain = new TH1F("hGain","",500,0,const_maxGain);
	hEnc = new TH1F("hEnc","",200,0,const_maxEnc);
	hGainVsChan = new TH1F("hGainVsChan","",const_numChan,0-0.5,const_numChan-0.5);
	hEncVsChan = new TH1F("hEncVsChan","",const_numChan,0-0.5,const_numChan-0.5);
}

void Analyze::doAnalysis(){
	//organize tree data by subrun
	std::cout << "Organizing data by subrun" << std::endl;
	organizeData();

	//analyze each channel
	for(unsigned int ch = 0 ; ch < const_numChan ; ch++)
		analyzeChannel(ch);

	//do summary analyses here
	identifyBadAsic();

	//output results
	outputResults();
}

void Analyze::organizeData(){
	//loop over tr_rawdata entries
  	Long64_t nEntries(tr_rawdata->GetEntries());
	tr_rawdata->GetEntry(0);
	//loop over input waveforms, group waveforms by subrun
	for(Long64_t entry(0); entry<nEntries; ++entry) { 
		tr_rawdata->GetEntry(entry);

		//make sure channels and subrun values are ok
		if( subrunIn < 0 || subrunIn >= const_numSubrun ) continue;
		if( chanIn < 0 || chanIn >= const_numChan ) continue;
		
		//store waveform vector in array for quick access
		for( unsigned int s = 0 ; s < wfIn->size() ; s++ )
			wfAll[subrunIn][chanIn].push_back( wfIn->at(s) );
  	}//entries
}

void Analyze::analyzeChannel(unsigned int chan){
	if( chan % 10 == 0 )
		std::cout << "Analyzing channel " << chan << std::endl;

	//do basic noise measurement
	ffer_analyzePulses.measureNoise( wfAll[0][chan] );
	double meanSubrun0 = ffer_analyzePulses.baseMean;
	double rmsSubrun0 = ffer_analyzePulses.baseRms;

	//fill basic noise measurement histograms
	pMeanVsChan->Fill( chan, meanSubrun0 );
	pRmsVsChan->Fill(chan, rmsSubrun0);
	//get overall sample distribution for low level debugging
	for( int s = 0 ; s < wfAll[0][chan].size() ; s++ ){
		unsigned short samp =  wfAll[0][chan].at(s);
		hSampVsChan->Fill( chan, samp);
	}

	//determine if channel is bad, don't try to measure gain
	if( rmsSubrun0 <= 0 ){
		identifyBadChannel(chan,meanSubrun0,rmsSubrun0,0);
		return;
	}

	//compute FFT if channel passes basic check
	computeFft(chan, wfAll[0][chan]);

	//loop over pulser settings
	ffer_analyzePulses.enablePulseFits = const_doFits;
	for(unsigned int sr = 1 ; sr < const_numSubrun ; sr++){
		//drawWf(chan,wfAll[sr][chan]);

		//find pulses
		findPulses(wfAll[sr][chan],meanSubrun0,rmsSubrun0);

		ffer_analyzePulses.clearData();
		ffer_analyzePulses.setBaseMeanRms(meanSubrun0, rmsSubrun0);
		ffer_analyzePulses.addData( 0,  pulseRiseStart, wfAll[sr][chan] );
		ffer_analyzePulses.analyzePulses();

		getAveragePulseHeight( ffer_analyzePulses.pulseHeights );

		//skip subrun if invalid pulse height measured
		if( averagePulseHeight < 0 )
			continue;
		if( averagePulseHeight > const_maxPulseHeightForFit )
			ffer_analyzePulses.enablePulseFits = 0;
		double signalCharge = (signalSizes[sr]-signalSizes[0]);
		gPulseVsSignal[chan]->SetPoint( gPulseVsSignal[chan]->GetN() , signalCharge , averagePulseHeight );

		getAveragePulseHeight( ffer_analyzePulses.fitPulseHeights );
		if( averagePulseHeight > 0 )
			gFitPulseVsSignal[chan]->SetPoint( gFitPulseVsSignal[chan]->GetN() , signalCharge , averagePulseHeight );
	}

	//measure channel gain
	measureGain(chan,rmsSubrun0);
	hGainVsChan->SetBinContent(chan+1, measuredGain);
	hEncVsChan->SetBinContent(chan+1, measuredEnc);
	hGain->Fill(measuredGain);
	hEnc->Fill(measuredEnc);

	//identify if channel is bad
	identifyBadChannel(chan,meanSubrun0,rmsSubrun0,measuredGain);
}

//draw waveform if wanted
void Analyze::drawWf(unsigned int chan, const std::vector<unsigned short> &wf){
	if( wf.size() == 0 ) return;
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
	char ct;
	std::cin >> ct;
	usleep(1000);
}

void Analyze::computeFft(unsigned int chan, const std::vector<unsigned short> &wf){
	if( chan >= const_numChan )
		return;
	if( wf.size() == 0 )
		return;
	//load hits into TGraph, skip stuck codes
	gCh->Set(0);
	for( int s = 0 ; s < wf.size() ; s++ ){
		//if( !isGoodCodeif( wf.at(s) ) continue;
		gCh->SetPoint(gCh->GetN() , s , wf.at(s) );
	}

	//compute FFT - use TGraph to interpolate between missing samples
	//int numFftBins = wf.size();
	int numFftBins = const_numFftBins;
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
		double freq = const_samplingRate* i / (double) hFftData->GetNbinsX() ;
		pFFTVsChan->Fill( chan, freq,  hFftData->GetBinContent(i+1) );
	}

	delete hData;
	delete hFftData;
}

void Analyze::findPulses(const std::vector<unsigned short> &wf, double baseMean, double baseRms){
	if( wf.size() == 0 )
		return;
	if( baseRms <= 0 )
		return;

	//look for pulses along waveform, hardcoded number might be bad
	double threshold = 5*baseRms;
	if( threshold < const_minThreshold )
		threshold = const_minThreshold;
	int numPulse = 0;
	pulseRiseStart.clear();
	pulseFallStart.clear();
	for( int s = 0 + const_preRange ; s < wf.size() - const_postRange - 1 ; s++ ){
		//if( !isGoodCodeif( wf.at(s) ) continue;
		//if( !isGoodCodeif( wf.at(s+1) ) continue;
		double value =  wf.at(s);
		double valueNext = wf.at(s+1);
		//simple threshold test
		if(1 && valueNext > baseMean + threshold && value < baseMean + threshold ){ //rising edge
			int start = s;
			pulseRiseStart.push_back(start );
		}
		if(1 && valueNext < baseMean - threshold && value > baseMean - threshold ){ //falling edge
			int start = s;
			pulseFallStart.push_back(start );
		}
	}
}

void Analyze::getAveragePulseHeight(const std::vector<double> &pulseHeights){
	averagePulseHeight = -1;
	if( pulseHeights.size() < const_minNumberPulses )
		return;

	hPulseHeights->Reset();

	for( int p = 0 ; p < pulseHeights.size() ; p++ )
		hPulseHeights->Fill( pulseHeights.at(p) );

	//get average pulse height
	hPulseHeights->GetXaxis()->SetRangeUser(0.5,const_maxPulseHeight-0.5);
	averagePulseHeight = hPulseHeights->GetMean();
	return;
}

void Analyze::measureGain(unsigned int chan, double baseRms){
	measuredGain = -1;
	measuredEnc = -1;
	if( gPulseVsSignal[chan]->GetN() < 1 ) 
		return;
	if( baseRms <= 0 )
		return;

	TF1 *f1 = new TF1("f1","pol1",100.E+3,200.E+3);
	gPulseVsSignal[chan]->Fit("f1","QR");

	//check if fit succeeded here

	double gain_AdcPerE = f1->GetParameter(1);
	double gain_ePerAdc = 0;
	if( gain_AdcPerE > 0 )
		gain_ePerAdc = 1./ gain_AdcPerE;
	if( gain_ePerAdc > const_maxGain )
		gain_ePerAdc = 0;
	double enc = baseRms*gain_ePerAdc;

	measuredGain = gain_ePerAdc;
	measuredEnc = enc;
	
	if(0){
		std::cout << gain_ePerAdc << std::endl;
		std::cout<< enc << std::endl;
		c0->Clear();
		gPulseVsSignal[chan]->Draw("ALP");
		c0->Update();
		char ct;
		std::cin >> ct;
	}

	delete f1;

	return;
}

void Analyze::identifyBadChannel(unsigned int chan, double baseMean, double baseRms, double gain){
	if( chan >= const_numChan )
		return;

	bool isBadChannel = 0;
	if( baseRms <= 0 )
		isBadChannel = 1;
	if( gain <= 0 )
		isBadChannel = 1;

        //baseline additional cuts
	//if( baseMean < 2250 )
	//	isBadChannel = 1;
	//if( baseMean > 8000 )
	///	isBadChannel = 1;
	//if( baseMean > 3400 && baseMean < 7000 )
	//	isBadChannel = 1;

	//RMS additional cuts
 	//if( baseRms > 40.4 )
	//	isBadChannel = 1;

	//gain additional cuts
	if( gain > 400 )
		isBadChannel = 1;
	if( gain < 10 )
		isBadChannel = 1;

	badChannelMask[chan] = isBadChannel;

	return;
}

void Analyze::identifyBadAsic(){
        //do final selection cuts, should put in indiviudl function
	int numBadAsic0Channels = 0;
	int numBadAsic1Channels = 0;
	int numBadAsic2Channels = 0;
	int numBadAsic3Channels = 0;
        for(int ch = 0 ; ch < const_numChan ; ch++ ){
		if( badChannelMask[ch] == 1 ){
			if( ch >= 0 && ch < 16 ){
				numBadAsic0Channels++;
			}
			if( ch >= 16 && ch < 32 ){
				numBadAsic1Channels++;
			}
			if( ch >= 32 && ch < 48 ){
				numBadAsic2Channels++;
			}
			if( ch >= 48 && ch < 64 ){
				numBadAsic3Channels++;
			}
		}
	}
	if( numBadAsic0Channels > const_cut_numBadChannels )
		badAsicMask[0] = 1;
	if( numBadAsic1Channels > const_cut_numBadChannels )
		badAsicMask[1] = 1;
	if( numBadAsic2Channels > const_cut_numBadChannels )
		badAsicMask[2] = 1;
	if( numBadAsic3Channels > const_cut_numBadChannels )
		badAsicMask[3] = 1;
}

void Analyze::outputResults(){
	//make a text file summarizing results
	writeToTextFile();

	//make a summary plot
	makeSummaryPlot();

  	//output ROOT histograms, data objects
	writeToRootFile();
}

void Analyze::writeToTextFile(){
	//output to file here:
  	std::string outputFileName = "output_processNtuple_gainMeasurement.list";
	ofstream listfile;
        listfile.open (outputFileName);
  	//ASIC results
        listfile << "asic " << "0" << "," << "fail " << badAsicMask[0] << std::endl;
        listfile << "asic " << "1" << "," << "fail " << badAsicMask[1] << std::endl;
        listfile << "asic " << "2" << "," << "fail " << badAsicMask[2] << std::endl;
        listfile << "asic " << "3" << "," << "fail " << badAsicMask[3] << std::endl;
  	//channel results
	for(int ch = 0 ; ch < const_numChan ; ch++ ){
		listfile << "ch " << ch << ",";
		listfile << "rms " << pRmsVsChan->GetBinContent(ch+1) << ",";
		listfile << "mean " << pMeanVsChan->GetBinContent(ch+1) << ",";
		listfile << "gain " << hGainVsChan->GetBinContent(ch+1) << ",";
		listfile << "enc " << hEncVsChan->GetBinContent(ch+1) << ",";
		listfile << "fail " << badChannelMask[ch];
		listfile << std::endl;
	}
        listfile.close();
}

void Analyze::makeSummaryPlot(){
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
	//c0->Divide(2,3);
        c0->Divide(2,2);
	
	c0->cd(1);
	pMeanVsChan->Draw();
	
	c0->cd(2);
	pFFTVsChan->Draw("COLZ");
	
	c0->cd(3);
	hGainVsChan->Draw();

	c0->cd(4);
	hEncVsChan->Draw();

	c0->Update();

	//save summary plots
	TImage *img = TImage::Create();
	img->FromPad(c0);
  	std::stringstream imgstream;
	imgstream << "summaryPlot_gainMeasurement.png";
	std::string imgstring( imgstream.str() );
  	img->WriteImage(imgstring.c_str());
}

void Analyze::writeToRootFile(){
	if( !gOut )
		return;

 	gOut->Cd("");
	c0->Write("c0_SummaryPlot");
  	hSampVsChan->Write();
	pMeanVsChan->Write();
  	pRmsVsChan->Write();
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

	for(int ch = 0 ; ch < const_numChan ; ch++ ){
		std::string title = "gPulseHeightVsSignal_Ch_" + to_string( ch );
		gPulseVsSignal[ch]->GetXaxis()->SetTitle("Number of Electrons (e-)");
		gPulseVsSignal[ch]->GetYaxis()->SetTitle("Measured Pulse Height (ADC counts)");
		gPulseVsSignal[ch]->Write(title.c_str());

		title = "gFitPulseHeightVsSignal_Ch_" + to_string( ch );
		gFitPulseVsSignal[ch]->GetXaxis()->SetTitle("Number of Electrons (e-)");
		gFitPulseVsSignal[ch]->GetYaxis()->SetTitle("Measured Pulse Height (ADC counts)");
		gFitPulseVsSignal[ch]->Write(title.c_str());
	}

	//write subrun specific objects
  	gOut->Close();
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

  gROOT->SetBatch(true);
  //define ROOT application object
  theApp = new TApplication("App", &argc, argv);
  processNtuple(inputFileName); 

  //return 1;
  gSystem->Exit(0);
}
