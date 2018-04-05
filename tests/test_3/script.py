# Multivariate Time Series Forecasting with LSTMs
#
# Summary
#-------------------------------------------------------------------------------
# Import data and categorize the bikes, change LSTM layers' settings
# Doesn't predict well, it learns the values and repeats the previous interval

################################################################################
# Libraries and Imports
################################################################################

from math import sqrt
import numpy
import pandas
import matplotlib.pyplot as plt
from numpy import concatenate
from sklearn.preprocessing import MinMaxScaler, LabelEncoder, OneHotEncoder
from sklearn.metrics import mean_squared_error
from pandas import concat,DataFrame, read_csv
from keras.models import Sequential
from keras.utils import plot_model, to_categorical
from keras import optimizers
from keras.layers import Dense, LSTM, Activation
from datetime import datetime
import datetime
from numpy import argmax

################################################################################
# Global Variables
################################################################################

stationToRead = 'ZUNZUNEGI'
is_in_debug = True
weekdays = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

lstm_neurons = 100
batch_size   = 20
epochs       = 10

################################################################################
# Classes and Functions
################################################################################

# Colorful prints in the terminal
class col:
    HEADER    = '\033[95m'
    blue      = '\033[94m'
    green     = '\033[92m'
    yellow    = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'

# Formatted output
def print_smth(description, x):
    
    if is_in_debug == True:
        print "", col.yellow
        print description
        print "----------------------------------------------------------------------------", col.ENDC
        print x
        print col.yellow, "----------------------------------------------------------------------------", col.ENDC

# Formatted output
def print_array(description, x):
    
    if is_in_debug == True:
        print "", col.yellow
        print description, " ", x.shape
        print "----------------------------------------------------------------------------", col.ENDC
        print x
        print col.yellow, "----------------------------------------------------------------------------", col.ENDC


# Convert series to supervised learning
# Arguments
#  * [Columns]> Array of strings to name the supervised transformation
def series_to_supervised(columns, data, n_in=1, n_out=1, dropnan=True):

    n_vars = 1 if type(data) is list else data.shape[1]
    dataset = DataFrame(data)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(dataset.shift(i))
        names += [(columns[j] + '(t-%d)' % (i)) for j in range(n_vars)]

    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(dataset.shift(-i))
        if i == 0:
            #names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
                    names += [(columns[j] + '(t)') for j in range(n_vars)]
        else:
                    names += [(columns[j] + '(t+%d)' % (i)) for j in range(n_vars)]
    # put it all together
    agg = concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)

    print_smth("Reframed dataset after converting series to supervised", agg.head())

    print agg.columns

    return agg


def prepare_plot(xlabel, ylabel, min_y, max_y):

    plt.figure(figsize=(12, 9))
    ax = plt.subplot(111)
    ax = plt.axes(frameon=False)

    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()


    plt.xlabel(xlabel, color = 'silver')
    plt.ylabel(ylabel, color = 'silver')

# Calculates the number of incorrect samples
def calculate_no_errors(predicted, real):

    print predicted
    print real

    wrong_val = 0

    for i in range(0, len(predicted)):
        if predicted[i] != real[i]:
            wrong_val += 1

    print wrong_val, "/", len(predicted)

print col.HEADER
print "   __            __     _____"
print "  / /____  _____/ /_   |__  /"
print " / __/ _ \/ ___/ __/    /_ < "
print "/ /_/  __(__  ) /_    ___/ / "
print "\__/\___/____/\__/   /____/  ", col.ENDC                           

################################################################################
# Data preparation
################################################################################

print col.HEADER + "Data reading and preparation" + col.ENDC

#--------------------------------------------------------------------------------
# File reading, drop non-relevant columns like station id, station name...
#--------------------------------------------------------------------------------

dataset         = pandas.read_csv('Bilbao.txt')
dataset.columns = ['datetime', 'weekday', 'id', 'station', 'free_bikes', 'free_docks'] 
dataset         = dataset[dataset['station'].isin([stationToRead])]

print col.HEADER, "> Data from " + dataset['datetime'].iloc[0], " to ", dataset['datetime'].iloc[len(dataset) - 1], col.ENDC

print_smth("Read dataset", dataset.head())

dataset.drop(dataset.columns[[2,3,5]], axis = 1, inplace = True)

dataset = dataset.reset_index(drop = True)
values  = dataset.values

#--------------------------------------------------------------------------------
#-- Data reading ----------------------------------------------------------------
#
# Split datetime column into day of the year and time
#--------------------------------------------------------------------------------

times = [x.split(" ")[1] for x in values[:,0]]

dataset['datetime'] = [datetime.datetime.strptime(x, '%Y/%m/%d %H:%M').timetuple().tm_yday for x in values[:,0]]

dataset.insert(loc = 1, column = 'time', value = times)

values  = dataset.values

print_smth("Dataset with unwanted columns removed", dataset.head())

#--------------------------------------------------------------------------------
#-- Data encoding ---------------------------------------------------------------
#
# Integer encode day of the year and hour and normalize the columns
#--------------------------------------------------------------------------------

hour_encoder    = LabelEncoder()                     # Encode columns that are not numbers
weekday_encoder = LabelEncoder()                     # Encode columns that are not numbers

values[:,1] = hour_encoder.fit_transform(values[:,1]) # Encode HOUR as an integer value
values[:,2] = weekday_encoder.fit_transform(values[:,2]) # Encode HOUR as int

max_bikes = max(values[:,3]) # Maximum number of bikes a station holds
max_cases = max_bikes + 1

values    = values.astype('float32')           # Convert al values to floats

print_smth("Prescaled values", values)
print values.shape

oneHot = to_categorical(values[:,3])

values = values[:,:-1]

scaler = MinMaxScaler(feature_range=(0,1))  # Normalize values
scaled = scaler.fit_transform(values)

print_smth("Deleted column", scaled)

scaled = numpy.append(scaled, oneHot, axis = 1)

print_smth("Dataset with normalized values", scaled)

#--------------------------------------------------------------------------------
# Generate the columns list for the supervised transformation
#--------------------------------------------------------------------------------


# Columns names for the transformation from time series to supervised learning
columns = ['doy', 'time', 'weekday']

# Generate same number of columns for the categorization problem as bikes are in this station
for i in range(0, max_bikes + 1):
    columns.append(str(i) + '_free_bikes')

print columns
print len(columns)

n_in = 100
n_out = 1

reframed = series_to_supervised(columns, scaled, n_in, n_out)

# Drop columns that I don't want to predict, every (t) column except free_bikes(t)

to_drop = range((max_cases + 3) * n_in, (max_cases + 3) * n_in + 3)

reframed.drop(reframed.columns[to_drop], axis=1, inplace=True)

values = reframed.values

print_smth("Reframed dataset without columns that are not going to be predicted", reframed.head())

print reframed.columns


train_size, test_size, prediction_size = int(len(values) * 0.65) , int(len(values) * 0.3), int(len(values) * 0.05)

train_size = int(int(train_size / batch_size) * batch_size) 
test_size = int(int(test_size / batch_size) * batch_size) 
prediction_size = int(int(prediction_size / batch_size) * batch_size) 


# Divide between train and test sets
train, test, prediction = values[0:train_size,:], values[train_size:train_size + test_size, :], values[train_size + test_size:train_size + test_size + prediction_size, :]


output_vals = range(n_in * (max_cases + 3),n_in * (max_cases + 3) + n_out * max_cases)

print(output_vals)

#--------------------------------------------------------------------------------
#--------------------------------------------------------------------------------
#--------------------------------------------------------------------------------

# data_size = int(len(values))
# train_size_initial = int(data_size * train_size)
# x_samples = values[-data_size:, :]

# if train_size_initial < batch_size_div:
#     batch_size = 1
# else:
#     batch_size = int(train_size_initial / batch_size_div)
# train_size = int(int(train_size_initial / batch_size) * batch_size)  # provide even division of training / batches
# val_size = int(int((data_size - train_size) / batch_size) * batch_size)  # provide even division of val / batches
# print('Data Size: {}  Train Size: {}   Batch Size: {}'.format(data_size, train_size, batch_size))

# train, val = x_samples[0:train_size, 0:-1], x_samples[train_size:train_size + val_size, 0:-1]


#--------------------------------------------------------------------------------
#--------------------------------------------------------------------------------
#--------------------------------------------------------------------------------



train_x, train_y           = train[:,range(0,(max_cases+3) * n_in)], train[:,output_vals]
test_x, test_y             = test[:,range(0,(max_cases+3) * n_in)], test[:,output_vals]

prediction_x, prediction_y = prediction[:,range(0,(max_cases+3) * n_in)], prediction[:,output_vals]

print_array("TRAIN_X ", train_x)
print_array("TRAIN_Y ", train_y)
print_array("TEST_X ", test_x)
print_array("TEST_Y ", test_y)
print_array("PREDICTION_X ", prediction_x)
print_array("PREDICTION_Y ", prediction_y)

# reshape input to be [samples, time_steps, features]
train_x = train_x.reshape((train_x.shape[0], n_in, max_cases +3)) # (...,1,4)
test_x  = test_x.reshape((test_x.shape[0], n_in, max_cases +3))    # (...,1,4)
prediction_x  = prediction_x.reshape((prediction_x.shape[0], n_in, max_cases +3))    # (...,1,4)

print_array("TRAIN_X 2 ", train_x)
print_array("TRAIN_Y 2 ", train_y)
print_array("TEST_X 2 ", test_x)
print_array("TEST_Y 2 ", test_y)
print_array("PREDICTION_X 2 ", prediction_x)
print_array("PREDICTION_Y 2 ", prediction_y)

print col.blue, "[Dimensions]> ", "Train X ", train_x.shape, "Train Y ", train_y.shape, "Test X ", test_x.shape, "Test Y ", test_y.shape, "Prediction X", prediction_x.shape, "Prediction Y", prediction_y.shape, col.ENDC

################################################################################
# Neural Network
################################################################################

print col.HEADER + "Neural Network definition" + col.ENDC

#--------------------------------------------------------------------------------
# Parameters
#--------------------------------------------------------------------------------
# lstm_neurons = 100
# batch_size   = 50
# epochs       = 10


#--------------------------------------------------------------------------------
# Network definition
#--------------------------------------------------------------------------------
model = Sequential()
# model.add(LSTM(lstm_neurons, input_shape = (train_x.shape[1], train_x.shape[2]), return_sequences = False, stateful = False))
model.add(LSTM(lstm_neurons, batch_input_shape=(batch_size, train_x.shape[1], train_x.shape[2]), return_sequences=False, stateful=True))
model.add(Dense(max_cases * n_out, activation='softmax'))
model.compile(loss = 'categorical_crossentropy', optimizer = 'adam', metrics = ['accuracy'])


history = model.fit(train_x, train_y, epochs = epochs, batch_size = batch_size, 
    validation_data = (test_x, test_y), verbose = 2, shuffle = True)

model.save('test_3.h5')

plot_model(model, to_file='plots/model.png', show_shapes = True)
print col.HEADER + "> Saved model shape to an image" + col.ENDC

#--------------------------------------------------------------------------------
# Predicted data (yhat)
#--------------------------------------------------------------------------------

min_y = min(history.history['loss'])
max_y = max(history.history['loss'])

yhat   = model.predict(test_x, batch_size = batch_size)

#-----------------------------------

# invert to_categorical
yhat = argmax(yhat, axis = 1)
yhat = yhat.reshape(len(yhat),1)

print_smth("yhat", yhat)
print yhat.shape

test_x = test_x.reshape((test_x.shape[0], test_x.shape[2] * n_in))
test_x = test_x[:,[0,1,2]]

print test_x

inv_yhat = scaler.inverse_transform(test_x)

inv_yhat = concatenate((inv_yhat, yhat), axis=1)

print_smth("inv_yhat before cast", inv_yhat)

#--------------------------------------------------------------------------------
# Real data (inv_yhat)
#--------------------------------------------------------------------------------

print_smth("HEYEYE AYFSADFA", test_y)

yhat = argmax(test_y, axis = 1)
yhat = yhat.reshape(len(yhat),1)

# Real values
inv_y = scaler.inverse_transform(test_x)
inv_y = concatenate((inv_y, yhat), axis=1)

print_smth("inv_y before cast", inv_y)

# Cast the bikes as ints
inv_yhat = inv_yhat[:,3].astype(int)
inv_y    = inv_y[:,3].astype(int) 

print_smth("inv_y after casting to int the bikes", inv_y)
print_smth("inv_yhat after casting to int the bikes", inv_yhat)

# Calculate RMSE
rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
print col.HEADER + '> Test RMSE: %.3f' % rmse + col.ENDC

calculate_no_errors(inv_y, inv_yhat)

################################################################################
# Plot styling
################################################################################

#--------------------------------------------------------------------------------
# Loss Plot
#--------------------------------------------------------------------------------

prepare_plot('epochs', 'loss', min_y, max_y)

lines  = plt.plot(history.history['loss'], label = 'train', color = '#458DE1')
lines += plt.plot(history.history['val_loss'], label = 'test', color = '#80C797')

plt.setp(lines, linewidth=2)

plt.text((len(history.history['loss']) - 1) * 1.005,
         history.history['loss'][len(history.history['loss']) - 1] + 0.01,
         "Training Loss", color = '#458DE1')

plt.text((len(history.history['val_loss']) - 1) * 1.005,
         history.history['val_loss'][len(history.history['val_loss']) - 1],
         "Validation Loss", color = '#80C797')

texto = "RMSE " +  str('%.3f' % (rmse))  + " | Batch size " + str(batch_size) + " | Epochs " + str(epochs) + " |  " + str(lstm_neurons) + " LSTM neurons"
plt.title(texto,color="black", alpha=0.3)
plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')

plt.savefig("plots/loss.png", bbox_inches="tight")
plt.close()
print col.HEADER + "> Loss plot saved" + col.ENDC

#--------------------------------------------------------------------------------
# Accuracy Plot
#--------------------------------------------------------------------------------

prepare_plot('epoch', 'accuracy', min_y, max_y)

plt.title(texto,color="black", alpha=0.3)

lines = plt.plot(history.history['acc'], color = '#458DE1')
lines += plt.plot(history.history['val_acc'], color = '#80C797')

plt.setp(lines, linewidth=3)

plt.text((len(history.history['acc']) - 1) * 1.005,
         history.history['acc'][len(history.history['loss']) - 1],
         "Training Accuracy", color = '#458DE1')

plt.text((len(history.history['val_acc']) - 1) * 1.005,
         history.history['val_acc'][len(history.history['val_loss']) - 1],
         "Validation Accuracy", color = '#80C797')

plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')
plt.savefig("plots/acc.png", bbox_inches="tight")
plt.close()
print col.HEADER + "> Accuracy plot saved" + col.ENDC

#--------------------------------------------------------------------------------
# Training Plot
#--------------------------------------------------------------------------------

min_y = min(inv_y)
max_y = max(inv_y)

prepare_plot('samples', 'bikes', min_y, max_y)

plt.title(texto, color="black", alpha=0.3)

lines = plt.plot(inv_yhat, color = '#458DE1')
lines += plt.plot(inv_y, label = 'inv_y', color = '#80C797')
plt.setp(lines, linewidth=2)


plt.text((len(inv_yhat) - 1) * 1.005,
         inv_yhat[len(inv_yhat) - 1],
         "Predicted set", color = '#458DE1')

plt.text((len(inv_y) - 1) * 1.005,
         inv_y[len(inv_y) - 1],
         "Training set", color = '#80C797')

plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')

plt.savefig("plots/train.png", bbox_inches="tight")
# plt.show()
plt.close()
print col.HEADER + "> Training plot saved" + col.ENDC

print inv_y[range(5384,5394)]

#--------------------------------------------------------------------------------
# Zoomed
#--------------------------------------------------------------------------------

min_y = min(inv_y)
max_y = max(inv_y)

prepare_plot('samples', 'bikes', min_y, max_y)

plt.title(texto,color="black", alpha=0.3)

init = 5100

lines = plt.plot(inv_y[range(init,init + 500)], color = '#458DE1')
lines += plt.plot(inv_yhat[range(init,init + 500)], label = 'inv_y', color = '#80C797')
plt.setp(lines, linewidth=2)
plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')

plt.savefig("plots/train_zoomed.png", bbox_inches="tight")
# plt.show()
plt.close()
print col.HEADER + "> Training plot saved" + col.ENDC

################################################################################
# Value predictions
################################################################################

print_array("Prediction IN", prediction_x)

yhat   = model.predict(prediction_x, batch_size = batch_size)

print_array("Prediction OUT", yhat)

# invert to_categorical
yhat = argmax(yhat, axis = 1)
yhat = yhat.reshape(len(yhat),1)

prediction_x = prediction_x.reshape((prediction_x.shape[0], prediction_x.shape[2] * n_in))
prediction_x = prediction_x[:,[0,1,2]]


inv_yhat = scaler.inverse_transform(prediction_x)

inv_yhat = concatenate((inv_yhat, yhat), axis=1)

print_smth("inv_yhat before cast", inv_yhat)

#--------------------------------------------------------------------------------
# Real data (inv_yhat)
#--------------------------------------------------------------------------------

print_smth("HEYEYE AYFSADFA", prediction_y)

yhat = argmax(prediction_y, axis = 1)
yhat = yhat.reshape(len(yhat),1)

# Real values
inv_y = scaler.inverse_transform(prediction_x)
inv_y = concatenate((inv_y, yhat), axis=1)

print_smth("inv_y before cast", inv_y)

# Cast the bikes as ints
inv_yhat = inv_yhat[:,3].astype(int)
inv_y    = inv_y[:,3].astype(int) 

print_smth("inv_y after casting to int the bikes", inv_y)
print_smth("inv_yhat after casting to int the bikes", inv_yhat)

# Calculate RMSE
rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
print col.HEADER + '> Test RMSE: %.3f' % rmse + col.ENDC

calculate_no_errors(inv_y, inv_yhat)

################################################################################
# Plot styling
################################################################################

#--------------------------------------------------------------------------------
# Loss Plot
#--------------------------------------------------------------------------------

prepare_plot('epochs', 'loss', min_y, max_y)

lines  = plt.plot(history.history['loss'], label = 'train', color = '#458DE1')
lines += plt.plot(history.history['val_loss'], label = 'test', color = '#80C797')

plt.setp(lines, linewidth=2)

plt.text((len(history.history['loss']) - 1) * 1.005,
         history.history['loss'][len(history.history['loss']) - 1] + 0.01,
         "Training Loss", color = '#458DE1')

plt.text((len(history.history['val_loss']) - 1) * 1.005,
         history.history['val_loss'][len(history.history['val_loss']) - 1],
         "Validation Loss", color = '#80C797')

texto = "RMSE " +  str('%.3f' % (rmse))  + " | Batch size " + str(batch_size) + " | Epochs " + str(epochs) + " |  " + str(lstm_neurons) + " LSTM neurons"
plt.title(texto,color="black", alpha=0.3)
plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')

plt.savefig("plots/loss_22222.png", bbox_inches="tight")
plt.close()
print col.HEADER + "> Loss plot saved" + col.ENDC

#--------------------------------------------------------------------------------
# Accuracy Plot
#--------------------------------------------------------------------------------

prepare_plot('epoch', 'accuracy', min_y, max_y)

plt.title(texto,color="black", alpha=0.3)

lines = plt.plot(history.history['acc'], color = '#458DE1')
lines += plt.plot(history.history['val_acc'], color = '#80C797')

plt.setp(lines, linewidth=3)

plt.text((len(history.history['acc']) - 1) * 1.005,
         history.history['acc'][len(history.history['loss']) - 1],
         "Training Accuracy", color = '#458DE1')

plt.text((len(history.history['val_acc']) - 1) * 1.005,
         history.history['val_acc'][len(history.history['val_loss']) - 1],
         "Validation Accuracy", color = '#80C797')

plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')
plt.savefig("plots/acc_22222.png", bbox_inches="tight")
plt.close()
print col.HEADER + "> Accuracy plot saved" + col.ENDC

#--------------------------------------------------------------------------------
# Training Plot
#--------------------------------------------------------------------------------

min_y = min(inv_y)
max_y = max(inv_y)

prepare_plot('samples', 'bikes', min_y, max_y)

plt.title(texto, color="black", alpha=0.3)

lines = plt.plot(inv_yhat, color = '#458DE1')
lines += plt.plot(inv_y, label = 'inv_y', color = '#80C797')
plt.setp(lines, linewidth=2)


plt.text((len(inv_yhat) - 1) * 1.005,
         inv_yhat[len(inv_yhat) - 1],
         "Predicted set", color = '#458DE1')

plt.text((len(inv_y) - 1) * 1.005,
         inv_y[len(inv_y) - 1],
         "Training set", color = '#80C797')

plt.tick_params(bottom="off", top="off", labelbottom="on", left="off", right="off", labelleft="on", colors = 'silver')

plt.savefig("plots/train_222222.png", bbox_inches="tight")
# plt.show()
plt.close()
print col.HEADER + "> Training plot saved" + col.ENDC


################################################################################
# Predictron
################################################################################

# Makes future predictions by doing iterations, takes some real initial samples
# makes a prediction and then uses the prediction to predict

print col.BOLD, "\n\n------------------------------------------------------------------------"
print "Predicting a whole day of availability"
print "------------------------------------------------------------------------\n\n", col.ENDC


print_smth("test_x", test_x)

print_smth("test_x[0]", test_x[0])

print_smth("test_x[0][0]", test_x[0][0])

today   = datetime.datetime.now().timetuple().tm_yday # Current day of the year
weekday = weekdays[datetime.datetime.today().weekday()]
hour    = "00:00"
inital_bikes = 10

hour = hour_encoder.transform([hour])[0]
weekday = weekday_encoder.transform([weekday])[0]
inital_bikes = to_categorical(inital_bikes, max_cases)

three_main = numpy.array(today)
three_main = numpy.append(three_main, hour)
three_main = numpy.append(three_main, weekday)

data_in = scaler.transform([three_main])

data_in = numpy.append(data_in, inital_bikes)


data2 = numpy.array([data_in])

print data2, data2.shape

# data2 = numpy.append(data2, [data_in], axis = 1)

# print data2, data2.shape

# If there are more than one time-steps create the initial array
if n_in > 1:
    for ts in range(1,n_in):
        print("Timestep" + str(ts))
        three_main[1] += 1
        data_in = scaler.transform([three_main])
        data_in = numpy.append(data_in, inital_bikes)

        data2 = numpy.append(data2, [data_in], axis = 1)


data2 = data2.reshape((data2.shape[0], n_in, max_cases +3)) # (...,1,4)

print_array("Data2",  data2)

auxxx = data2


for i in range(batch_size - 1):
    # print i
    data2 = numpy.append(data2, auxxx, axis = 1)    

    print_array("Data2 " + str(i),  data2)



data2 = data2.reshape((batch_size, n_in, max_cases +3)) # (...,1,4)
print_array("Data2",  data2)

# print data2, data2.shape

data_predicted = []


for i in range(0,240):

    print col.FAIL, ">>> Prediction n." + str(i), col.ENDC

    aux = data2[0][:,range(0, 3)][0]

    # print_smth("data2", aux) # Get the first sample of the input

    aux2 = scaler.inverse_transform([aux])
    hora = hour_encoder.inverse_transform(aux2[:,1].astype(int))[0] # Encode HOUR as an integer value
    print "-----------"

    data2 = data2.reshape((-1, n_in, max_cases +3)) # (...,1,4)

    print_array("DATA2 PRE PREDICT", data2)

    pred =  model.predict(data2, batch_size = batch_size)

    pred = pred[0]
    # print_array("PRED", pred[0])
    print "Predichas ", argmax(pred), " bicis a las ", hora


    data_predicted.append(argmax(pred))

    three_main[1] += 1 # increase hour interval
    data_in = scaler.transform([three_main])

    print_array("data_in", data_in)


    data2 = data2[0]

    print_array("DADADATA2", data2)

    data2 = data2.reshape((1, n_in * (max_cases +3))) # (...,1,4)
    data2 = data2[:,range(max_cases+3, n_in*(max_cases+3))]

    print_array("DADADATA2", data2)

    # print "Deleted ", data2, data2.shape

    bikes = to_categorical(argmax(pred), max_cases)
    data_in = numpy.append(data_in, bikes)
    data2 = numpy.append(data2, [data_in], axis = 1)
    data2 = data2.reshape((data2.shape[0], n_in, max_cases +3)) # (...,1,4)

    for i in range(batch_size - 1):
        # print i
        data2 = numpy.append(data2, auxxx, axis = 1)    

    
    print_array("Data2 " + str(i),  data2)

    # print ">>>>> ", data2, data2.shape



print data_predicted


