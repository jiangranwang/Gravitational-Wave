import datetime
import tensorflow as tf
import numpy as np
import h5py
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import math
import sys
from Noiser import Noiser
from Net import FixNet, FixNet2
from Batch import get_batch, get_val
import os
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

test_num = '1'
if len(sys.argv) > 1:
    test_num = sys.argv[1]

if len(sys.argv) > 2 and sys.argv[2] == "file":
    stdoutOrigin=sys.stdout 
    sys.stdout = open("testOut"+test_num+".txt", "w")

f_train = h5py.File("data/twoSecondTrain.h5", "r")
f_test = h5py.File("data/twoSecondTest.h5", "r")
tf.logging.set_verbosity(tf.logging.ERROR)

input_data = tf.placeholder(tf.float32, [None, 8192, 1])
input_label = tf.placeholder(tf.int32, [None,2])
trainable = tf.placeholder(tf.bool)

# loss function operations
predictions = FixNet2(input_data, trainable)
loss = tf.losses.mean_squared_error(input_label, predictions)

# train operation
global_step = tf.Variable(0, trainable=False)
learning_rate = tf.train.exponential_decay(learning_rate=0.0001, 
                                           global_step=global_step, 
                                           decay_steps=len(f_train['m1m2'])//64, 
                                           decay_rate=0.96, 
                                           staircase=True)

optimizer = tf.train.AdamOptimizer(learning_rate=0.0001)
train_op = optimizer.minimize(
    loss=loss,
    global_step=global_step)

#initialization
init = tf.global_variables_initializer()
saver = tf.train.Saver()
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
sess = tf.Session(config=config)
sess.run(init)
loss_hist = []
val_loss = []
#saver.restore(sess, "../model/test2.ckpt")

num_epoch = 1000
start = datetime.datetime.now()
batch_size = 64
real_noise = False  #change here!
# len(snr) = 50
low = [0.6,0.5,0.4,0.4,0.3,0.3,0.3,0.2,0.2,0.2,0.1,0.1]
snrs = [5.0,4.0,3.0,2.0,1.7,1.5,1.4,1.3,1.2,1.1,1.0,0.9,0.8,0.7] + [lows for lows in low for i in range(3)]
for i in range(num_epoch):
    snr = snrs[i//20]
    train_data, train_label = get_batch(f_train, batch_size, real_noise=real_noise, SNR=snr)
    for j in range(len(train_data)):
        cur_data = train_data[j]
        cur_label = train_label[j]
        _, loss_val = sess.run([train_op, loss],
                           feed_dict={input_data: cur_data,
                                      input_label: cur_label,
                                      trainable: True})
        loss_hist.append(loss_val)
        if j % 10 == 0:
            print('loss: '+str(loss_hist[-1]))
    
    val_data, val_label = get_val(f_test, batch_size, real_noise=real_noise, SNR=snr)
    validation = sess.run(loss, feed_dict={input_data: val_data, input_label: val_label, trainable: False})
    val_loss.append(validation)
    print('iter num: '+str(i)+' snr: '+str(snr)+' loss: '+str(loss_hist[-1])+' val_loss: '+str(val_loss[-1]))
    
end = datetime.datetime.now()
print('time: '+str(end-start))

#save model
save_path = saver.save(sess, '../model/test'+test_num+'.ckpt')
print("Model saved in path: %s" % save_path)

step = 9861//batch_size
axis = np.arange(step-1, len(loss_hist), step)
plt.figure()
plt.plot(loss_hist)
plt.scatter(axis, val_loss, c = 'red')
plt.legend(['train_loss','val_loss'], loc=1)
plt.title('loss history--total time: '+str(end-start))
plt.xlabel('epochs')
plt.ylabel('loss')
plt.savefig(test_num+'testLoss.png')


def plot(sess, snrs, f_test, fig, shift=None):
    def showplot(pred,name):
        test_label = np.asarray(f_test['m1m2'])
        error1 = [abs(pred.T[0][i]-test_label.T[0][i])/test_label.T[0][i] for i in range(len(test_label))]
        error2 = [abs(pred.T[1][i]-test_label.T[1][i])/test_label.T[1][i] for i in range(len(test_label))]
        plt.figure(figsize=(18,20))
        cm = plt.cm.get_cmap('seismic')
        plt.subplot(211)
        sc = plt.scatter(test_label.T[0], test_label.T[1], c=error1, vmin=0.0025, vmax=0.75, 
                         cmap=cm, norm=colors.LogNorm(vmin=np.amin(error1), vmax=np.amax(error1)))
        plt.colorbar(sc)
        plt.xlabel('m1 mass')
        plt.ylabel('m2 mass')
        plt.title(name)
        plt.subplot(212)
        sc = plt.scatter(test_label.T[0], test_label.T[1], c=error2, vmin=0.0025, vmax=0.75, 
                         cmap=cm, norm=colors.LogNorm(vmin=np.amin(error2), vmax=np.amax(error2)))
        plt.colorbar(sc)
        plt.xlabel('m1 mass')
        plt.ylabel('m2 mass')
        plt.title(name)
        plt.savefig(name+'.png')

    #testing without shift
    start = 0
    end = 8192
    print("shift is: ", shift)
    noise = Noiser()
    m1s = []
    m2s = []
    for i in range(len(snrs)):
        pred = []
        for j in range(len(f_test['data'])):
            test_data = f_test['data'][j][start:end].reshape(1,end-start)
            test_data = noise.add_shift(test_data)
            if shift is not None:
                test_data[0][:shift[0]] = 0
                test_data[0][shift[1]:] = 0
            if real_noise is False:
                test_data = noise.add_noise(input=test_data, SNR=snrs[i])
            else:
                test_data = noise.add_real_noise(input=test_data, SNR=snrs[i])
            test_data = test_data.reshape(1,end-start,1)
            test_label = f_test['m1m2'][j].reshape(1,2)

            pred.append(sess.run(predictions, feed_dict={input_data: test_data, input_label: test_label, trainable: False})[0])
        pred = np.asarray(pred)
        test_label = np.asarray(f_test['m1m2'])
        m1 = np.mean(np.divide(abs(pred.T[0]-test_label.T[0]),test_label.T[0]))
        m2 = np.mean(np.divide(abs(pred.T[1]-test_label.T[1]),test_label.T[1]))
        m1s.append(m1)
        m2s.append(m2)
        print('SNR: '+str(snrs[i])+' -- m1: '+"{0:.5%}".format(m1)+' m2: '+"{0:.5%}".format(m2))
        #if i % 51 == 0:
        #   showplot(pred,'testSNR--'+fig+str(snrs[i]))

    m1s = np.asarray(m1s)
    m2s = np.asarray(m2s)
    plt.figure()
    plt.plot(np.flip(snrs, 0),np.flip(m1s*100, 0))
    plt.plot(np.flip(snrs, 0),np.flip(m2s*100, 0))
    plt.legend(['m1','m2'], loc=1)
    plt.xlabel('SNR')
    plt.ylabel('Relative Error')
    plt.title('RE with SNR')
    plt.savefig(fig+'.png')

snrs = np.linspace(5.0,0.1,249)
plot(sess, snrs, f_test, test_num+'0.5-1.0s', shift=[int(8192*0.5), int(8192*1.0)])
plot(sess, snrs, f_test, test_num+'0.0-0.5s', shift=[int(8192*0.0), int(8192*0.5)])
plot(sess, snrs, f_test, test_num+'0.0-0.25s', shift=[int(8192*0.0), int(8192*0.25)])
plot(sess, snrs, f_test, test_num+'0.25-0.5s', shift=[int(8192*0.25), int(8192*0.5)])
plot(sess, snrs, f_test, test_num+'0.5-0.75s', shift=[int(8192*0.5), int(8192*0.75)])
plot(sess, snrs, f_test, test_num+'0.75-1.0s', shift=[int(8192*0.75), int(8192*1.0)])
plot(sess, snrs, f_test, test_num+'0.7-0.9s', shift=[int(8192*0.7), int(8192*0.9)])
plot(sess, snrs, f_test, test_num+'0.0-1.0s')
