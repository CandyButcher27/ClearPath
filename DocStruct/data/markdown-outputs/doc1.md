matter

***

## Predicting Concentration Levels of Air Pollutants by Transfer

## Learning and Recurrent Neural Network

Iat Hang Fonga, Tengyue Lia, Simon Fonga, Raymond K. Wongb, Antonio J. Tallón-Ballesterosc,*

aDepartment of Computer and Information Science, University of Macau, Taipa, China.

bFaculty of Engineering, University of New South Wales, Sydney. Australia.

cDepartment of Languages and Computer Systems, University of Seville, Seville, Spain.

Abstract Air pollution (AP) poses a great threat to human health, and people are paying more attention than

ever to its prediction. Accurate prediction of AP helps people to plan for their outdoor activities and aids

protecting human health. In this paper, long-short term memory (LSTM) recurrent neural networks (RNNs)

have been used to predict the future concentration of air pollutants (APS) in Macau. Additionally,

meteorological data and data on the concentration of APS have been utilized. Moreover, in Macau, some air

quality monitoring stations (AQMSs) have less observed data in quantity, and, at the same time, some

AQMSs recorded less observed data of certain types of APS. Therefore, the transfer learning and pre-trained

neural networks have been employed to assist AQMSs with less observed data to build a neural network with

high prediction accuracy. The experimental sample covers a period longer than 12-year and includes daily

measurements from several APS as well as other more classical meteorological values. Records from five

stations, four out of them are AQMSs and the remaining one is an automatic weather station, have been

prepared from the aforesaid period and eventually underwent to computational intelligence techniques to

build and extract a prediction knowledge-based system. As shown by experimentation, LSTM RNNs

initialized with transfer learning methods have higher prediction accuracy; it incurred shorter training time

than randomly initialized recurrent neural networks. Keywords Forecasting, environment monitoring, transfer learning, recurrent neural network, airborne particle

Corresponding author. Tel: +34 954556237; fax: +34 954557139. Postal address: Reina Mercedes AV. 41012, Seville,

*Spain. Email address: atallon@us.es (A.J. Tallón-Ballesteros)*

1

---

1. Introduction With the development of societies and industries, many countries and cities in the world have to face

the problem of air pollution (AP), which has been bringing many undesirable effects on human health.

Therefore, predicting the AP level in the cities and then publishing the severity of air pollution to the public

is important. Air pollutants (APS) mainly come from burning fossil fuels. They are mainly encompassing

), nitrogen monoxide (NO), nitrogen dioxide (NO ), carbon monoxide (CO),

sulphur dioxide (SO

*2*

*2*

inhalable particles with diameters which are generally 10 micrometers and smaller (PM ), fine inhalable

*10*

), etc. Indeed, PM stands for

particles with diameters which are generally 2.5 micrometers and smaller (PM

*2.5*

airborne particulate matter and its study is now on the rise especially to the current problem of the climate

change associated to the vehicle emission and free-fuel transport. As we all know, AP adversely affects

people's health, especially children and the elderly; it will also make patients with respiratory diseases, such

as asthma and bronchitis, or cardiovascular disease, worse. In addition, prolonged exposure to traffic-related

air pollution may shorten life expectancy. Moreover, people who go through long-term exposure to vehicle-

related AP may have their life expectancy shortened [1]. Xi Chen et al. [2] studied the relationship between

, SO , and PM concentrations and lung cancer mortality in several northern cities in China, as well as

NO

*2 2 10*

the relationship between these APS and patients with lung cancer. The statistical data they have researched

show that the concentration of air pollutants in people's area is positively correlated with the prevalence and

mortality of lung cancer. Atmosphere state and AP have a great relationship; for example, when the atmosphere is stable, that

is to say, when the air in a certain area is not rising, the APS will stay on the surface, which is unfavorable to

the spread of air pollutants. On the contrary, if the atmosphere is unstable, the air will move upward

vertically, which will help the APS to spread to the sky. The atmosphere state is usually measured with

seven different elements, namely wind speed, wind run, atmospheric temperature, relative humidity, dew

point temperature, atmospheric pressure and precipitation. People usually employ automatic weather stations

(AWSs) – also called meteorological monitoring stations – to measure automatically and periodically the

above-mentioned seven atmospheric elements. Besides, air quality monitoring stations (AQMSs) are used to

, SO , NO, etc. in a certain area automatically

measure the concentration of APS such as PM

*2.5 2*

and periodically. Magnitudes measured by AWSs and AQMSs along with their units are listed in Table 1.

*Figure 1 (a) displays the locations of AQMSs in Macao [3], the following AQMSs have been used in*

this paper: High density residential area (Macao), Roadside (Macao), Ambient (Taipa), High

density residential area (Taipa). Figure 1 (b) shows the locations of AWSs in Macao. Taipa Grande AWS has

been utilized in this research. The observed data of the AQMSs and AWS in the circles with bullets in green

and blue depicted in Figure 1 are used for the experimentation of this paper. , SO and NO

AP seriously affects public health. By letting people know the AP level such as PM

*2.5 2 2*

in advance, they gain advantage and then they can plan for outdoor activities conveniently and protect

people's health. Long-short term memory recurrent neural networks (LSTM RNNs) are used in this paper to

predict the situations of AP in the future. LSTM RNNs are good at predicting time series data, and the

concentration of APS can be considered as time series data. Hence, in order to be able to predict the already

2

---

that can be extended. name of features

air quality monitoring station inhalable particles (PM10)

fine inhalable particles (PM2.5)

nitrogen monoxide (NO)

Nitrogen dioxide (NO2)

carbon monoxide (CO)

automatic weather station wind speed

wind run

station atmospheric pressure

air temperature

relative humidity

mentioned concentration of APS – despite the lack of knowledge about the atmospheric dispersion modeling

of APS – LSTM RNN has been applied in this paper. Additionally, in order to obtain good prediction results even though the lack of observed data,

transfer learning has been proposed to be used in this paper to assist predicting the AP level. The

LSTM RNNs have been trained in a domain (source domain) with more observed data as usual in data

mining and knowledge-based systems, and then use the trained networks for the tasks with less observed data

(target domain). The objective of this paper is to investigate the difference, in terms of prediction errors, between our

proposed method and the original method. The original method is to randomly initialize a neural network to

do the prediction. The proposed method is to pre-train a neural work using transfer learning, with similar

data from nearby stations that have certain correlation with the predicted results. The research question

is whether or not to use pre-trained neural network methods. The remaining of this paper is arranged as follows. Related works are introduced in Section 2. In

Section 3, the methodology along with the key ingredients such as the LSTM RNNs, transfer learning and

pre-trained neural networks are described. In Section 4, the details of the experiments are explained. Section

5 reports the experimental results and makes an analysis of experimental results. Section 6 draws the main

conclusion as a summary of the experiments in the paper, opening some future lines for further works

units

μg/m3

μg/m3

ppb

ppb

ppm

km/h

km

hPa

C

%

3

---

preccipitation

mmm

deww point

C

*Table 1. Features obsserved by Aiir Quality Monitoring Staation (AQMSS) and Autommatic Weathher Station*

(AWS).

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

Air qualityy monitoringg stations (AQQMSs) and ((b) automaticc weather staations

*Figure 1. (aa)*

(AWSs) in Macau..

2. Background

the one

may hhave many mmeanings ass well as appplication doomains. On hannd, from ann

Trannsfer engineeringg approach, a heat trannsfer from aan object too another one may occcur; additionnally in thee

communicaation field, thhe transfer could be donne in differennt ways like asynchronouus, synchronnous or evenn

mode. half-duplex or full-duplex OOn the otherr hand, in aartificial intelligence scooppe the learnning may bee

tto a subsequeent task; in thhis way, the first step iss the input foor the secondd

transferred ffrom a task output of thee

step. Althouugh transfer learning waas introducedd in the mid of the ninetiies from the previous ceentury, it hass

not receivedd a growing interest till 22018. The firrst special isssue published on an interrnational jouurnal is datedd

4

---

data from Hong Kong. They predicted APS comprising NO

future concentrations of APS covering CO, NO

neural network to predict the PM

*10*

in 1996 where a very extensive survey of transfer between connectionist networks was included [4].

Moreover, in the next year, that is 1997, a special issue attracted the attention from many researchers to dive

into the inductive transfer [5]. By its part, Sebastian Thrun and Lorien Pratt edited a book entitled “Learning

to Learn” in 1998 and Transfer Learning is addressed from four different points of views such as Overview,

Prediction, Relatedness and Control including thirteen chapters [6]; humans often generalise correctly after a

few of training examples by transferring knowledge acquired in other tasks; systems that learn to learn

mimic this ability. During the period from 1998 to 2006, the topic remained in background. From 2007, it

has been recognised as an important theme within machine learning. Basically, it is what happens when

someone finds it much easier to learn to play chess having already learned to play checkers, or to recognize

*tables having already learned to recognize chairs [7]. Formally, transfer learning aims at providing a framework to make use of previously-acquired*

knowledge to solve new but similar problems much more quickly and effectively; in contrast to classical

machine learning methods, transfer learning approaches exploit the knowledge accumulated from data in

ancillary domains to facilitate predictive modelling consisting of different data patterns in the current domain

[8]. Continuing with the transfer learning timeline, Sinno Jian Pan and Qiang Yang published a survey about

the topic in 2009, and they studied extensively the inductive, transductive and unsupervised transfer learning

[9]. The following year, the Handbook of Research in Machine Learning Applications devoted a chapter

written by Lisa Torrey and Jude Shavlik to Transfer Learning to cover the inductive typology focusing on

inductive, Bayesian and Hierarchical Transfer as well as the missing data and class labels; perhaps the main

novelty of this work are the relationship with the reinforcement learning and the automatically mapping tasks

[10]. A publication in the scope of forecasting, more concretely in the field of crude oil price, saw the light in

2012 [11]. The current journal published the first manuscript on transfer learning in 2015 introducing a

transfer component analysis [12]; a newly paper falling in the survey category appeared also in 2015 which

made emphasis on the computational intelligence corner to do the transfer [8]. To follow, Karl Weiss et al.

wrote a survey paper with more than 140 references and a length of 40 pages in 2016 where some formal

definitions are provided and a very wide taxonomy of many types of transfer learning, such as the

homogeneous and the heterogeneous ones including, for each one, the asymmetric feature-based and

symmetric feature-based transfer learning; in the former the parameter-based one, the relational-based one

and the hybrid-based one are explained [13]. Stephan Spiegel opened a research line for Time Series

Classification in dissimilarity spaces in 2016 [14]. Furthermore, the temporal information was also

considered by Joseph Lemley et al. in the following year in the context of driver action classification [15].

Some months later, Ran Zhang et al. proposed neural networks to transfer the learning for bearing faults

diagnosis in changing working conditions [16]. A good proliferation of works happened in 2018 and hence

one may find insights for reconstruction and regression loss for time series [17] and frameworks based on

extreme learning machine to conduct the transfer [18]. Jiangshe Zhang et al. [19] proposed an extreme learning machine [20] to predict the concentration of

APS in two of locations in Hong Kong; they used a six-year air pollutant concentration and meteorological , NO , O , SO and PM . Ming Cai et al. [21]

*2 X 3 2 2.5*

utilized artificial neural network to forecast the hourly average concentration of APS in an arterial road in

Guangzhou; the authors used concentration data of APS, meteorological and traffic video data, etc. to predict

, PM and O . G. Grivas et al. [22] employed artificial

*2 10 3*

concentration in Athens, Greece. S.I.V. Sousa et al. [23] applied principal

component analysis [24] to pre-process the input data and then put it into an artificial neural network to

5

---

predict the O concentration Xiao Feng et al. [25] made use of a variety of techniques, including air mass

*3*

trajectory analysis [26] and wavelet transformation [27] to pre-process times series data, and then concentration. Because of

incorporated the training data into artificial neural network to estimate the PM

*2.5*

concentration in this area, the researchers used wavelet transformation to

the large variability of PM

*2.5*

and then obtained several time series with less variability; then each

decompose the time series for PM

*2.5*

time series is inputted to the neural network, and finally the prediction results of each neural network were

prediction result. Yu Zheng et al. [28] proposed a semi-supervised

combined together to obtain the PM

*2.5*

learning approach based on a co-training framework which consists of two separated classifiers, one is a

spatial classifier based on an artificial neural network, and the other one is a temporal classifier based on a

linear-chain Conditional Random Field (CRF). Bun Theang Ong et al. [29] applied deep recurrent neural

in Japan and employed auto-encoder as a pre-trained method to

network to predict PM

*2.5*

improve performance of deep recurrent neural network. Asha B Chelani et al. [30] utilized artificial neural

concentration in three cities in Delhi, they used the Levenberg–Marquardt

network to measure the SO

*2*

algorithm to train artificial neural networks. 3. Proposed methodology In this work, the prediction of the concentration of APS is considered as a time series prediction

problem and the LSTM RNNs is good for the time series prediction. Therefore, observed data from AWSs

and AQMSs in Macao, and LSTM RNNs are used to predict the level of air pollution in the future. All in July 2012. Therefore, the

AQMSs in Macau have officially begun to measure the concentration of PM

*2.5*

observed data for each station is relatively smaller than other APS. For some reasons, some

amount of PM

*2.5*

AQMSs will have more observed data, whilst some stations will have fewer observed data. For example, the

High density residential area (Taipa) AQMS suspended the air quality measurement from July 2012 to June

2013 due to the constructional engineering of the station nearby. Hence, it is suitable to transfer the

knowledge of the RNNs of AQMSs with more observation data to the RNNs of AQMSs with fewer

observation data. In our proposed design, the LSTM RNNs are used together to predict the concentration of

APS at an AQMS and transfer learning methods are applied to train neural networks. At first, the LSTM

RNNs are constructed and randomly initialized the weights of the LSTM; then observations of AWSs and

AQMSs are used as training data for the neural network; and then the prediction ability of the neural network

is evaluated. Then, the above-mentioned trained LSTM could be a pre-trained neural network for other

predictive tasks, and transfer the knowledge to new neural networks in target domains. The new tasks may be

predicting future concentration of certain APS – that can be the same or different from those of the source

domain – in other AQMSs, that can be the same or different from source domain. In the new task, another

LSTM is also constructed, and the weights of pre-trained neural network are used as the initial status of the

new task. Then we put new task-related data to train the new LSTM. The above-mentioned transfer learning

process is shown in the Figure 2. The training data includes the observed data from various AQMSs and an AWS in Macau. The

predicted target is the concentration of a certain air pollutant in an AQMS which is in the training data. In

this paper, the scenarios for using transfer learning are as follows: (1) Construction and training of a RNN in

) at an AQMS (e.g. Ambient (Taipa)); then using this

the source domain for a type of air pollutant (e.g. PM

*10*

6

---

neural netwwork as the ppre-trained neural networrk for anotheer air pollutaant (e.g. PMM ) of the saame AQMS..

*2.5*

That is, the task of the ttarget domaiin is predictiion of PM of the same AQMS. (2) Creation and training inn

*2.5*

ddomain for aan air pollutaant concentraation (e.g. PPM ) of an AAQMS (e.g. Ambient (TTaipa)). Thenn

the source

*10*

on the taskk of the targget domain, the above mmentioned RNNN becomes a pre-trainned network for anotherr

air pollutantt (e.g. PM ) of anotheer AQMS (ee.g. Roadsidde (Macau)); it is imporrtant to remmark that thee

*2.5*

distributions are very ssimilar in booth aforemenntioned situationns of the abbove transferr tasks. The differrent

at transfeerring the knnowledge off neural netwworks with mmore traininng data to the tasks withh

methods, aiim fewer trainning data. Inn our predicction, LSTMM RNNs aree trained to predict thee concentration of APS..

According to the article of Lisa TTorrey et all. [31], transsfer learningg can lead tto better iniitial trainingg

learning sppeed and higgher predictioon accuracy. Therefore, iit was expectted that transsfer learningg

status, fasteer would bringg the above-mentioned bbenefits for tthhe training pprocess and rresult of LSTTM RNNs. OOn the otherr

hand, somee AQMSs hhave less oobserved datta, so the trransfer learnning is appplied in thiss paper andd

eventually RRNNs obtainned good traiining results even in the ccase of less training data..

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figgure 2. The pprocess of trransfer learniing.*

4. Experimmentation settup Thee problem to this paper iis described as follows. TThere is a timme series daataset D, D ==

be solved inn {d , d , …, }, where ii=1, …, N, NN is the total that thhe dataset haas, and d = ((t, x), wheree

d number of reecords

*1 2 N*

*i i i*

is timestaamp, it repreesents a The innterval can bbe 24 hours,, 1 hour, 1 mminute, etc.;;

t certain time inteerval.

*i*

in this papeer, the time iinterval is 1 day. In addiition, x conttains meteoroological dataa of an AWSS, as well ass

*i*

data of conccentration off APS from multiple AQQMSs. Moreeover, the preedicted conccentration of APS is alsoo

included in x and thesee data are obtained at t tiimestamp. Inn this time t,, experiment, when there is a ceertain

*i i*

B time steeps of observved data beffore t, the obbserved data are useed to predictt

and there arre

of B days beefore

the concentrration value of air pollutaant in timestaamp t, as thee Figure 3 shows.

7

---

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figgure 3. Obseerved data froom the past sseveral days was used topredict futurre air pollutaants. and the*

Thee trained RNNN is represennted by p (.), conncentration vvalue of air ppollutant thatt is predictedd

by p (.) is reepresented byy y , as showwn in formulla (1).

*h,i*

(1))

> [Figure]

> [Figure]

In aaddition, the time series data consistts of the obsservation records from thhe AWS andd AQMSs inn

Macau, andd once the timme series data has been pproperly convverted, it cann become traiining, validaation and testt

data for RNNNs. The aboove data was obtained by submitting tthe applicatioon form to SSMG [32]. WWhat we wantt

to predict iss the concenttration of APPS of severall AQMSs intime series ddata. The folllowing is ann example off

conversion from time seeries data to LSTM trainiing data. As shown in Figure 4, supppose there is a time seriess

length N annd set B=6, then the timme series dataaset is conveerted to the ffollowing forrmat: (x , x ,,

dataset D of

*1 2*

, x , x , x , y ), (x , x , x , x , xx , y ), ..., (x , x , x ,x , x , x , y ); in thiss abstract exxample, eachh

, x x

3 4 5 66 7 2 3 4 5 6 7 8 nn-6 n-5 n-4 n-3 n-2 n-1 n

training datta is set to usse the data 6 days the air polluutant concenntrations on tthe next day..

before,, and predictt

Moreover, are tthe above examples thhe data convversion settinngs for each eexperiment inn this paper.

8

---

## 2nd

timestamp x y timestamp x y timestamp x y timestamp x y

2003-01-01 y 2003-01-01 y 2003-01-01 y 2003-01-01 y

x x

x x

*1 1 1 1*

2003-01-02 y 2003-01-02 y 2003-01-02 y 2003-01-02 y

x x

x x

*2 2 2 2*

2003-01-03 y 2003-01-03 y 2003-01-03 y 2003-01-03 y

*3 3 3 3*

2003-01-04 y 2003-01-04 y 2003-01-04 y 2003-01-04 y

*4 4 4 4*

2003-01-05 y 2003-01-05 y 2003-01-05 y 2003-01-05 y

*5 5 5 5*

2003-01-06 y 2003-01-06 y 2003-01-06 y 2003-01-06 y

*6 6 6 6*

2003-01-07 y 2003-01-07 y 2003-01-07 y 2003-01-07 y

*7 7 7 7*

2003-01-08 2003-01-08 y y 2003-01-08 y 2003-01-08 y

*8 8 8 8*

2003-01-09 y y 2003-01-09 y 2003-01-09 y

2003-01-09 x x

x x

*9 9 9 9*

2003-01-10 y y 2003-01-10 y 2003-01-10 y

2003-01-10 x x

x x

*10 10 10 10*

…

... ... ... ... ... ... ... ... ... ... ... ...

t y y t y t y

t y y t y t y

t y y t y t y

*Figure 4. Time series data is converted to training data for RNN.*

The architecture of all randomly initialized neural networks is shown in Figure 5. It is a concrete

example which we explain now; once all the features from AQMSs and AWS are combined, in a timestamp,

there are 41 columns given by AWS and AQMSs, and each row of the dataset used data 6 days ago from

each station. Figure 6 is an example about architecture of LSTM RNN in target domain. The top of RNNs in the

source domain are added the RNN layers that match the feature space of the target domain; the total number

of layers of neural networks in target domain is constant, but the number of neurons on the input layer and

layers will be changed according to the feature space that in target domain.

9

---

In oour work, somme LSTM RRNNs are ranndomly initiaalized their wweights and bbiases matricces, then aree

trained andd used to prredict APS. Each air pollutant wwill have a correspondiing RNN to predict itss

concentratioon, the PM , NO , NOO and PM of the Ambbient (Taipaa) AQMS annd the CO of the Highh

*110 2 2.5*

density residdential area (Macau) AQQMS are preedicted. The PM concentration of in our casee all AQMSs

*2.5*

has observeed data. So we will prrovide here for RNNNs which predict thee

pre-trained neural netwworks

concentratioon of PM of all AQMSs, and the ppre-trained nneural networks of sourcce domain innclude RNNss

*2.5*

for predictiing PM off Roadside ((Macau), PMM density rresidential arrea (Macau)) and PM of Ambientt

*10 10*

*10*

(Taipa), resppectively. AAbout High density resiidential areaa (Taipa) AAQMS, this iis a station with fewerr

observed daata, compareed to other AAQMSs. For tthis AQMS, the predicteed APS are PPM , NO , NNO and CO..

*2.5 2*

Moreover, randomly initialized nneural netwoorks and prre-trained nneural netwoorks method are usedd

to assess the performmances and rresults of thee two training methods. AAnother reasson for usingg

for compariison transfer leaarning is to uuse multiplee pre-trainedd neural netwworks for prredicting diffferent APS in the samee

AQMS as tthe source doomain, and tthen the targget domain iss predicting the PM off the same AAQMS to seee

*2.5*

how the trannsfer learninng works.

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figure 5. TThe architecture that is uused by all raandomly initiialized neuraal networks.*

10

---

Thee values of eeach feature in the datasset were resccaled, and thhen the obserrved data is put into thee

neural netwworks for traiining, validation and testt. The formuula (2) and (3) are the reescaling formmulas, wheree

X is the mminimum vaalue in a cerrtain feature,, X is the maximum vvalue in a ceertain featuree, R is thee

*min*

*max*

minimum vvalue after reescaled, andd R is the vvalue after rescaled. In tthis article, the rescaledd

maximum

*max*

ranges of alll features aree from 0 to 11.

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figuure 6. An exaample of RNNNN’s architecture trained nnetwork metthods. was part,*

In eeach experimment, the obsserved data dividedd into three pparts: the 1st approxximately thee

70% as trainning data; thhe 2nd part, 225% as the vaalidation datta; the 3rd paart, 5% as thee testing data. The studyy

period encoompasses moore than 12 yyears of 2001-2014; the starting and finishing daates are 1st OOctober 2001

and 1st Julyy 2014, resppectively, whhich cover 44,656 days wwith a daily sample and represent exxactly 12.755

years. Hencce, 9 years (771%) of sammples are thee training sett, 3 years (255%) of sampples act as vvalidation sett

and 0.75 yeears (5%) are set as the testing set.

11

*min*

(2)) (3))

---

5. Experimental results and analysis This section aims at presenting the results raised by the experimentation. Firstly, there is a

comparison between the new approach and the original procedure. Secondly, an alternative procedure and

the original approach are reported.

5.1. Base scenario The base scenario pursues to investigate the difference, in terms of prediction errors, between our

proposed method and the original method. The original method is to randomly initialize a neural network for

doing the prediction. The proposed method is to pre-train a neural work using transfer learning, with similar

data from nearby stations that have certain correlation with the predicted results. The experimental results,

measured in MSE, using training and validation data for randomly initialized networks and pre-trained

networks are tabulated in Table 2. The training results for various networks, including randomly initialized

for various AQMSs, and neural networks for various AQMSs that

neural networks that predicted PM

*2.5*

based on the PM pre-trained neural networks at all AQMSs are reported in Table 2. It can be

predict PM

*2.5 10*

seen that the neural networks that used pre-trained methods, and used the pre-trained network which is

) air pollutants and at different AQMSs, can indeed provide higher

predicting the same (or similar for PM

*2.5*

accuracy, faster learning speed and better initial learning state for neural networks.

*training data validation data*

*source domain target domain*

Best Best Initial MSE Initial MSE Best MSE Best MSE epoch epoch

12

---

*N/A*

Roadside (Macau) PM10 Roadside (Macau) PM2.5 High density residential area

*N/A*

Roadside (Macau) PM10 High density residential area (Macau) High density residential area

*(Macau) PM10*

*Ambient (Taipa) PM10*

initialized networks and pre-trained networks (PM ).

architecture of the latter corresponds to the former scenario.

*0.007266084 400 0.061714470 0.004698436 242 0.045378533*

*0.049579145 0.005730863 0.025669344 0.003596468 242 92*

*261 0.003505309 117 0.005546452 0.024579911 0.043278625*

(Macau) PM10 0.005549194 245 0.025933107 95 0.043425080 0.003466034

Ambient (Taipa) PM10 0.006227937 303 0.055660227 153 0.028110390 0.002996397

*0.031786795 0.004939886 0.021892348 0.003607673 168 18*

*0.003216892 188 38 0.004480842 0.021647959 0.026681633*

PM2.5 (Macau) PM10 0.004656768 171 0.021687523 0.003423001 21 0.027333746

Ambient (Taipa) PM10 0.007895702 368 0.059606799 0.007581763 197 0.045722324

*N/A 0.006281779 197 0.027147979 0.005756136 47 0.051130223*

Roadside (Macau) PM10 Ambient (Taipa) PM 2.5 High density residential area 0.005962373 0.027097617 186 0.005709018 36 0.040284840

*253 0.005752293 103 0.048785915 0.005713619 0.026958865*

*Table 2. Comparison of experimental results using training and validation data for randomly*

*2.5*

To illustrate the results, some charts are depicted in this second part of the paragraph. The research

question is whether or not after using pre-trained neural network methods, certain benefits may be achieved

as follows: (1) better initial state; (2) fewer epochs are required in training for convergence; and (3) better

predictive ability is reached. Figures 7, 9, 11, 12 show the comparison of real (observed data) and predicted

values. This set of charts shows that generally when the concentrations of APS were low, the predictions

were accurate. The reason is that the high concentration of air pollutants are outliers and RNNs were not

designed to deliberately cope with outliers during the training process. It can be seen from the other set of

*charts, depicted in Figures 8, 10, 13, which are trends of loss functions that use training data; in most cases,*

in terms of Best MSE and the number of epochs required to obtain the Best MSE, using pre-trained neural

networks were better than random initialized neural networks. Figure 10 is tied to Figure 6 given that the

13

---

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figure 7.. Comparisonn of real andd predicted vaalues in Ambbient (Taipa)) for PM .*

*10*

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

Comparisonn of the trendds of loss funnctions (usedd validation ddata, Ambiennt (Taipa) PMM ) – pre-

*Figure 8.*

*2.5*

traineed with data from multiple AQMSs PPM to Ambbient (Taipa) PM

*10 2.5*

14

---

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figure 9. Comparison of real andd predicted values in Ambbient (Taipa)) for NO .*

*2*

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

Comparisoon of the trennds of loss fuunctions of HHigh density residential aarrea (Taipa) NNO – pre-

*Figure 100.*

*2*

traineed from AQMMSs NO to High densityy residential area (Taipa)) NO .

*2*

*2*

15

---

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figuree 11. Comparrison of real and predicteed values in HHigh densityresidential aarea (Taipa) for NO.*

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figure 12. Comparrison of real aand predictedd values in HHigh density residential aarea (Taipa) ffor CO).*

16

---

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

Comparison of the trends of loss funnctions of Higgh density reesidential areea (Taipa) COO – pre-trainn

*Figure 13. CO to Higgh density reesidential areea (Taipa) COO.*

from AQMSSs

5.2. Alternaative scenarrio scenario Thee alternative prroposes the use of the of the targeet domain inn two ways:: input layer

trainable annd untrainablle. In the firsst case, the soource domaiin layer is set to trainablee and in the second case,,

the pre-trainned LSTM can be trainedd in the targeet domain. Fiigure 14 depiicts the alternnative scenarrio.

17

---

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

> [Figure]

*Figure 14. CChart of the alternative sscenario incluuding the tarrget domain.*

results conncerning the randomly innitialized networks and thhe alternativve scenario aare shown inn

Thee Table 3. Thhe experimenntal results reeveal that inn most cases, the prediction results ussing pre-trainned LSTMs,,

including trrainable and untrainable ppre-trained LLSTMs, will be better than randomlyy initialized LLSTMs. Thee

best results domain between eveery pair of ttrainable andd untrainablee, as well as the randomm

for each tarrget source dommains are higghlighted in bold font. TThe computattional cost off random iniitialization iss

initializationn in the ordeer the secondds and trainnable and unntrainable neetworks requuire a few mminutes to bbe processedd

completely..

*trainning data validation ddata*

sourrce domain targett domain Best Best Best MSE MSE Best MMSE Initial MSE Initial epoch epoch

18

---

400 0.061714470 0.004698436 242 0.045378533

0.007266084 N/A Roadside (Macau) PM10, pre-trained

77 0.04863139938 0.005182960193 2270.02527686319 0.00358629241

LSTM is trainable Roadside (Macau) PM10, pre-trained 0.005598728544 2080.029503071990.004178910752 60 0.02185823754

LSTM is untrainable High density residential area (Macau)

106 0.04286825121 0.004859869157 2560.024201206510.003472965484 Roadside (Macau) PM10, pre-trained LSTM is trainable PM 2.5 High density residential area (Macau) PM10, pre-trained LSTM is

0.02657779990.003741108357 0.005239599353 239 89 0.01998857462

untrainable Ambient (Taipa) PM10, pre-trained

0.04165692058 0.005092177982 2250.025583911140.003491097135 75

LSTM is trainable Ambient (Taipa) PM10, pre-trained 2600.028937639050.003937646276 110 0.00530908497 0.02238395186

LSTM is untrainable

303 0.055660227 153 0.028110390

0.006227937 0.002996397

N/A Roadside (Macau) PM10, pre-trained

18 0.03125582054 0.004569249764 1670.022118478920.003569208331

LSTM is trainable Roadside (Macau) PM10, pre-trained 0.00499207167 1600.025384787520.004096408385 10 0.01251311171

LSTM is untrainable High density residential area (Macau)

16 0.02638574313 0.004235766168 1660.021430666620.003448928911 High density residential PM10, pre-trained LSTM is trainable area (Macau) PM2.5 High density residential area (Macau) PM10, pre-trained LSTM is 0.004730619973 1560.023726921780.003976781423 6 0.01128700101

untrainable Ambient (Taipa) PM10, pre-trained 0.003870524781 2820.035359703610.005476613939 132 0.01998347242

LSTM is trainable Ambient (Taipa) PM10, pre-trained 3130.042807699820.005482501299 164 0.02113966902 0.00464007655 LSTM is untrainable

368 0.059606799 0.007581763 197 0.045722324

0.007895702 N/A Roadside (Macau) PM10, pre-trained

0.03692072487 0.005870847587 1870.026956356630.005757841261 37

LSTM is trainable Roadside (Macau) PM10, pre-trained 2040.030326688940.005965355129 54 0.005667415343 0.02517349517

LSTM is untrainable High density residential area (Macau)

0.03692072487 0.005870847587 1870.026956356630.005757841261 37

Ambient (Taipa) PM10, pre-trained LSTM is trainable PM 2.5 High density residential area (Macau) PM10, pre-trained LSTM is 2040.030326688940.005965355129 54 0.005667415343 0.02517349517

untrainable Ambient (Taipa) PM10, pre-trained

124 2300.026997903720.005343422969 0.005138671779 0.02564689896

LSTM is trainable Ambient (Taipa) PM10, pre-trained

0.04519483775 0.005666261346 80 2730.030443754910.005228251649

LSTM is untrainable

## Table 3. Comparison of experimental results for PM using training and validation data for

*2.5*

## randomly initialized networks and pre-trained LSTM in two ways: trainable and untrainble.

## 6. Conclusions and future work

## 19

---

In this paper, we proposed a type of transfer learning model that combines LSTM RNNs for

predicting air pollutant concentrations. The results from our experiments show that, pre-trained neural

network methods are helpful for training neural networks. In other words, the LSTM RNNs that are

initialized with pre-trained neural networks can achieve a higher level of prediction accuracy. Furthermore,

the number of epochs that are required to train a LSTM RNNs into convergence can be reduced. The new

method creates better initial states for RNNs. Our current experiments are concerned with predicting

the values of air pollutant concentration on the next day. As future work, the proposed method can be used in

training the RNNs to predict air pollution on the next several days ahead or even in a period shorter than one

day. Moreover, hourly-observed data could be used to predict hourly data in the next several hours for

enhancing the timely density of air pollution predictions.

The method proposed in the paper can also be used to predict other air pollutants, such as O

. These air pollutants predictors can be modified so that the predictor can be trained with the latest

SO

*2*

observed data continuously. The diversity of the data could be expanded to more observed data of AWSs and

AQMSs. Using other type of data, such as vehicle traffic data to predict concentration of APS of roadside by

AQMSs, etc. should be attempted. The prediction border could be expanded too. Observed data of AWSs

and AQMSs from Guangdong and Hong Kong can be used as training data instead of just using the

data locally in Macau. Residents nowadays are more concerned about the situation of serious AP, that is, the

situation of high concentration of APS. However, occurrence of serious AP is relatively rare and unusual,

and even these conditions are considered abnormal values (outliers). Therefore, some imbalanced dataset

processing methods can be used along with LSTM RNNs in future work, so that predictions can be made

more accurate prior to the AP scenarios.

Acknowledgement The authors are thankful to the financial support from the research grants, 1) MYRG2016-00069,

titled 'Nature-Inspired Computing and Metaheuristics Algorithms for Optimizing Data Mining Performance'

and 2) MYRG2016-00217, titled ‘Improving the Protein-Ligand Scoring Function for Molecular Docking by

Fuzzy Rule-based Machine Learning Approaches’ offered by University of Macau and Macau SAR

government.

References [1] Hoek, Gerard, et al. "Association between mortality and indicators of traffic-related air pollution in the

Netherlands: a cohort study." The lancet 360.9341 (2002): 1203-1209.

[2] Chen, Xi, et al. "Long-term exposure to urban air pollution and lung cancer mortality: A 12-year cohort

study in Northern China." Science of The Total Environment 571 (2016): 855-861.

20

and

*3*

---

[3] Automatic air quality monitoring stations in

Macau, http://www.smg.gov.mo/smg/airQuality/e_air_stations.htm [4] Pratt, Lorien, and Barbara Jennings. "A survey of transfer between connectionist networks." Connection

Science 8.2 (1996): 163-184. [5] Pratt, Lorien, and Sebastian Thrun. "Transfer in inductive systems." Machine Learning 28.1 (1997): 10-

1023. [6] Thrun, Sebastian, and Lorien Pratt. "Learning to learn: Introduction and overview." Learning to learn.

Springer, Boston, MA, 1998. 3-17. [7] Dai, Wenyuan, et al. "Boosting for transfer learning." Proceedings of the 24th international conference

on Machine learning. 2007. [8] Lu, Jie, et al. "Transfer learning using computational intelligence: A survey." Knowledge-Based Systems

80 (2015): 14-23. [9] Pan, Sinno Jialin, and Qiang Yang. "A survey on transfer learning." IEEE Transactions on knowledge

and data engineering 22.10 (2009): 1345-1359. [10] Torrey, Lisa, and Jude Shavlik. "Transfer learning." Handbook of research on machine learning

applications and trends: algorithms, methods, and techniques. IGI Global, 2010. 242-264.

[11] Xiao, Jin, Changzheng He, and Shouyang Wang. "Crude oil price forecasting: a transfer learning based

analog complexing model." 2012 Fifth International Conference on Business Intelligence and Financial

Engineering. IEEE, 2012. [12] Dai, Peng, Shen-Shyang Ho, and Frank Rudzicz. "Sequential behavior prediction based on hybrid

similarity and cross-user activity transfer." Knowledge-Based Systems 77 (2015): 29-39.

[13] Weiss, Karl, Taghi M. Khoshgoftaar, and DingDing Wang. "A survey of transfer learning." Journal of

Big data 3.1 (2016): 9. [14] Spiegel, Stephan. "Transfer learning for time series classification in dissimilarity spaces." Proceedings

of AALTD 2016: Second ECML/PKDD International Workshop on Advanced Analytics and Learning on

Temporal Data. Vol. 78. 2016. [15] Lemley, Joseph, Shabab Bazrafkan, and Peter Corcoran. "Transfer Learning of Temporal Information

for Driver Action Classification." MAICS. 2017. [16] Zhang, Ran, et al. "Transfer learning with neural networks for bearing fault diagnosis in changing

working conditions." IEEE Access 5 (2017): 14347-14357.

[17] Laptev, Nikolay, Jiafan Yu, and Ram Rajagopal. "Reconstruction and regression loss for time-series

transfer learning." Proc. SIGKDD MiLeTS. 2018.

[18] Ye, Rui, and Qun Dai. "A novel transfer learning framework for time series forecasting." Knowledge-

Based Systems 156 (2018): 74-99.

21

---

[19] Zhang, Jiangshe, and Weifu Ding. "Prediction of air pollutants concentration based on an extreme

learning machine: the case of Hong Kong." International journal of environmental research and public

health 14.2 (2017): 114. [20] Huang, Guang-Bin, Qin-Yu Zhu, and Chee-Kheong Siew. "Extreme learning machine: theory and

applications." Neurocomputing 70.1-3 (2006): 489-501.

[21] Cai, Ming, Yafeng Yin, and Min Xie. "Prediction of hourly air pollutant concentrations near urban

arterials using artificial neural network approach." Transportation Research Part D: Transport and

Environment 14.1 (2009): 32-41. [22] Grivas, G., and A. Chaloulakou. "Artificial neural network models for prediction of PM10 hourly

concentrations, in the Greater Area of Athens, Greece." Atmospheric environment 40.7 (2006): 1216-1229.

[23] Sousa, S. I. V., et al. "Multiple linear regression and artificial neural networks based on principal

components to predict ozone concentrations." Environmental Modelling & Software 22.1 (2007): 97-103.

[24] Wold, Svante, Kim Esbensen, and Paul Geladi. "Principal component analysis." Chemometrics and

intelligent laboratory systems 2.1-3 (1987): 37-52. [25] Feng, Xiao, et al. "Artificial neural networks forecasting of PM2. 5 pollution using air mass trajectory

based geographic model and wavelet transformation." Atmospheric Environment 107 (2015): 118-128.

[26] Stein, A. F., et al. "NOAA’s HYSPLIT atmospheric transport and dispersion modeling system." Bulletin

of the American Meteorological Society 96.12 (2015): 2059-2077.

[27] Pathak, R. S. "The Wavelet Transform. Atlantis studies in mathematics for engineering and science."

Atlantis Press 63 (2009): 64-65. [28] Zheng, Yu, Furui Liu, and Hsun-Ping Hsieh. "U-air: When urban air quality inference meets big data."

Proceedings of the 19th ACM SIGKDD international conference on Knowledge discovery and data mining.

2013. [29] Ong, Bun Theang, Komei Sugiura, and Koji Zettsu. "Dynamically pre-trained deep recurrent neural

networks using environmental monitoring data for predicting PM 2.5." Neural Computing and Applications

27.6 (2016): 1553-1566. [30] Chelani, Asha B., et al. "Prediction of sulphur dioxide concentration using artificial neural networks."

Environmental Modelling & Software 17.2 (2002): 159-166.

[31] Olivas, Emilio Soria, ed. Handbook of Research on Machine Learning Applications and Trends:

Algorithms, Methods, and Techniques: Algorithms, Methods, and Techniques. IGI Global, 2009.

[32] Macao Meteorological and Geophysical Bureau, Pedido

de dados, http://www.smg.gov.mo/www/ccaa/applyform/fc_infreq.htm

22
