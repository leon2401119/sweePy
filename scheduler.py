import threading
import subprocess
import numpy as np  # only for np.inf
import logging
from multiprocessing import cpu_count

class Scheduler:
    def __init__(self,num_workers=cpu_count()-1):
        self.used_jids = []
        self.jobs = {}            # dictionary of Popen Object for issued jobs, (cmd,inst_num) for queud jobs
        self.running = 0
        self.lock = threading.Lock()
        self.num_workers = num_workers

    def queue(self,*args):
        # acquire a unique job ID
        self.lock.acquire()
        new_jid = 0
        while True:
            if new_jid in self.used_jids:
                new_jid += 1
            else:
                break
        self.used_jids.append(new_jid)
        self.lock.release()

        job = args
        self.jobs[new_jid] = job
        logging.info(f'jid={new_jid} : Queued "{args}"')
        return new_jid

    def inquire(self,jid):
        try:
            job = self.jobs[jid]
        except KeyError:
            print('invalid job ID')
            raise()

        if type(job) is tuple:
            return None

        ret_code = job.poll() # check if process is ready
        
        if ret_code is None:
            return None
        elif ret_code == 0: # process exit normally
            self.lock.acquire()
            self.used_jids.remove(jid)
            self.running -= 1
            self.lock.release()

            self.jobs.pop(jid)
            logging.info(f'jid={jid} : Returned 0')
            return job.communicate()[0].decode('utf-8') # decode stdout
        else:  # FIXME : post-mortem, what is left to do?
            #print('sth unexpected')
            logging.error(f'jid={jid} : Returned {ret_code}')
            exit()

    def schedule(self): # pick jobs from queud jobs to schedule
        if self.running == self.num_workers:
            return

        pending_jobs = [(jid,self.jobs[jid][0],self.jobs[jid][1],self.jobs[jid][2]) for jid in list(self.jobs.keys()) if type(self.jobs[jid]) is tuple]
        if not len(pending_jobs):
            return

        pending_jobs.sort(key=lambda e:e[2] if type(e[2]) is int else np.inf) # sort by inst number
        while len(pending_jobs): # schedule one-by-one until workers are fed (or out of jobs)
            if self.running == self.num_workers:
                break

            self.lock.acquire()
            self.running += 1
            jid, cmd, cwd, inst_num = pending_jobs[0]
            self.jobs[jid] = subprocess.Popen(cmd.split(),cwd=cwd,env={"DSMGA2_INSTANCE_NUMBER":str(inst_num)},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            self.lock.release()
           
            logging.info(f'jid={jid} : Scheduled' + f' for thread {inst_num}' if inst_num is not None else '')
            #print(f'Scheduled job for thread {inst_num}')
            pending_jobs.pop(0)
