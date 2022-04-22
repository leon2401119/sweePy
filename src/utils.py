import numpy as np
import time

def get_moving_avg(data,k):
    assert k%2, 'k must be odd for centered moving average'
    assert k<len(data)

    newdata = []
    for i,v in enumerate(data):
        if v is np.nan:
            newdata.append(np.nan)
        else:
            cdata = data[i:]
            break

    window = [i for i in cdata[:k//2]]
    for i,v in enumerate(cdata):
        if i < k//2 + 1:
            window.append(cdata[i+k//2])
        elif i > len(cdata) - k//2 - 1:
            window.pop(0)
        else:
            window.append(cdata[i+k//2])
            window.pop(0)

        newdata.append(sum(window)/len(window))

    return newdata


def K_incr_in_mv_avg(data,K): # check if there are K consecutive increases in moving average extracted from data
    counter = 0
    if len(data.keys()) >= K + 1:
        nfe_list = []
        for pop in sorted(data.keys()):
            nfe_list.append(data[pop]['nfe'])

        smoothed_nfe_list = get_moving_avg(nfe_list,K)
        for i in range(len(smoothed_nfe_list)-1):
            if smoothed_nfe_list[i] < smoothed_nfe_list[i+1]:
                counter += 1
            else:
                couter = 0
            if counter == K:
                return True

    return False


def format_DSMGA2_output(result_str):
    stats = result_str.split('\n')[1]
    gen,_,nfe,_,lsnfe,failnum = stats.split(' ')
    gen = float(gen) if 'nan' not in gen else -1
    nfe = float(nfe) if 'nan' not in nfe else -1
    lsnfe = float(lsnfe) if 'nan' not in lsnfe else -1
    failnum = int(failnum)
    return [gen,nfe,lsnfe,failnum]
