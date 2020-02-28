from noiser import *
import numpy as np

keyStr = 'data'
NUM_DATA = 9840


def get_batch(f, k, length, real_noise=False, snr=None, shift=None):
    """
    :param f: hdf5 file object to get file
    :param k: batch size
    :param length: length of output starting from 0
    :param real_noise: whether to add real noise or generated noise
    :param snr: lowest snr value for current batch
    :param shift: whether zero out some portion of output
    :return: output batch, output label
    """

    # return array initialization
    batch = []
    label = []

    # constant initialization
    idx = np.arange(NUM_DATA)
    np.random.shuffle(idx)
    noise = Noiser(length)
    num_batch = NUM_DATA // k
    high = 3.0

    # initialize snr values
    snrArr = np.zeros(num_batch)
    if snr is not None:
        if snr > high:
            high = snr
        snrArr = np.random.uniform(low=snr, high=high, size=num_batch)

    # loop to get batch
    for i in range(num_batch):
        cur_batch = []
        cur_label = []
        for j in range(k):
            cur_batch.append(f[keyStr][idx[k * i + j]][:length])
            cur_label.append(f['m1m2'][idx[k * i + j]])
        cur_batch = noise.add_shift(cur_batch)
        if shift is not None:
            cur_batch.T[:shift[0]] = 0
            cur_batch.T[shift[1]:] = 0
        if snr is not None:
            if real_noise is False:
                cur_batch = noise.add_noise(input=cur_batch, SNR=snrArr[i])
            else:
                cur_batch = noise.add_real_noise(input=cur_batch, SNR=snrArr[i])

        batch.append(cur_batch)
        label.append(cur_label)

    # reshape
    batch = np.asarray(batch).reshape(num_batch, k, length, 1)
    label = np.asarray(label)
    return batch, label


def get_val(f, k, length, real_noise=False, snr=None, shift=None):
    """
    :param f: hdf5 file object to get file
    :param k: batch size
    :param length: length of output starting from 0
    :param real_noise: whether to add real noise or generated noise
    :param snr: lowest snr value for current batch
    :param shift: whether zero out some portion of output
    :return: output batch, output label
    """

    batch = []
    label = []

    # constant initialization
    idx = np.random.choice(f[keyStr].shape[0], k, replace=False)
    noise = Noiser(length)

    # loop to get batch
    for i in range(k):
        batch.append(f[keyStr][idx[i]][:length])
        label.append(f['m1m2'][idx[i]])
    if shift is not None:
        np.asarray(batch).T[:shift[0]] = 0
        np.asarray(batch).T[shift[1]:] = 0
    if snr is not None:
        snrArr = np.random.uniform(low=snr, high=snr, size=1)[0]
        if real_noise is False:
            batch = noise.add_noise(input=batch, SNR=snrArr)
        else:
            batch = noise.add_real_noise(input=batch, SNR=snrArr)
    batch = noise.add_shift(batch)
    batch = np.asarray(batch).reshape(k, length, 1)
    label = np.asarray(label)
    return batch, label


def get_classify_batch(f, k, length, real_noise, snr):
    """
    :param f: hdf5 file object to get file
    :param k: batch size
    :param length: length of output starting from 0
    :param real_noise: whether to add real noise or generated noise
    :param snr: lowest snr value for current batch
    :return: output batch, output label (Noise, Signal)
    """

    # return array initialization
    batch = []
    label = []

    # constant initialization
    idx = np.arange(NUM_DATA)
    np.random.shuffle(idx)
    noise = Noiser(length)
    num_batch = NUM_DATA // k
    ratios = np.random.uniform(size=num_batch)
    ratioArr = np.array([int(ratio * k) for ratio in ratios])
    high = 3.0

    # initialize snr values
    if snr > high:
        high = snr
    snrArr = np.random.uniform(low=snr, high=high, size=num_batch)

    # loop to get batch
    for i in range(num_batch):
        zero = []
        signal = []
        cur_label = []
        for j in range(k):
            rand = np.random.uniform(low=0.0, high=1.0)
            if rand < 0.6:
                zero.append(np.zeros(length))
                cur_label.append([1, 0])
                continue
            signal.append(f[keyStr][idx[k * i + j]][:length])
            cur_label.append([0, 1])

        if real_noise is False:
            if len(signal) is not 0:
                signal = noise.add_noise(input=signal, SNR=snrArr[i])
            if len(zero) is not 0:
                zero = noise.add_noise(input=zero, SNR=snrArr[i])
        else:
            if len(signal) is not 0:
                signal = noise.add_real_noise(input=signal, SNR=snrArr[i])
            if len(zero) is not 0:
                zero = noise.add_real_noise(input=zero, SNR=snrArr[i])
        cur_batch = np.array(list(zero) + list(signal))
        cur_batch = noise.add_shift(cur_batch)

        idxCurr = np.arange(k)
        np.random.shuffle(idxCurr)
        cur_batch = [cur_batch[a] for a in idxCurr]
        cur_label = [cur_label[a] for a in idxCurr]
        batch.append(cur_batch)
        label.append(cur_label)

    # reshape
    batch = np.asarray(batch).reshape(num_batch, k, length, 1)
    label = np.asarray(label)
    return batch, label


def get_classify_val(f, k, length, real_noise, snr):
    """
    :param f: hdf5 file object to get file
    :param k: batch size
    :param length: length of output starting from 0
    :param real_noise: whether to add real noise or generated noise
    :param snr: lowest snr value for current batch
    :return: output batch, output label (Noise, Signal)
    """

    signal = []
    zero = []
    label = []

    # constant initialization
    idx = np.random.choice(f[keyStr].shape[0], k, replace=False)
    noise = Noiser(length)

    # loop to get batch
    counter = 0
    for i in range(k):
        # use half and half during testing
        if counter < k // 2:
            zero.append(np.zeros(length))
            label.append([1, 0])
            counter += 1
            continue
        signal.append(f[keyStr][idx[i]][:length])
        label.append([0, 1])

    snrArr = np.random.uniform(low=snr, high=snr, size=1)[0]
    if real_noise is False:
        signal = noise.add_noise(input=signal, SNR=snrArr)
        zero = noise.add_noise(input=zero, SNR=snrArr)
    else:
        signal = noise.add_real_noise(input=signal, SNR=snrArr)
        zero = noise.add_real_noise(input=zero, SNR=snrArr)
    batch = np.array(list(zero) + list(signal))

    batch = noise.add_shift(batch)

    batch = np.asarray(batch).reshape(k, length, 1)
    label = np.asarray(label)
    return batch, label
