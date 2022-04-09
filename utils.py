import numpy as np

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


def format_DSMGA2_output(result_str):
    stats = result_str.split('\n')[1]
    gen,_,nfe,_,lsnfe,failnum = stats.split(' ')
    gen = float(gen) if 'nan' not in gen else -1
    nfe = float(nfe) if 'nan' not in nfe else -1
    lsnfe = float(lsnfe) if 'nan' not in lsnfe else -1
    failnum = int(failnum)
    return [gen,nfe,lsnfe,failnum]
