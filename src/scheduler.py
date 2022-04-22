import threading
import subprocess
import numpy as np  # only for np.inf
import logging
from multiprocessing import cpu_count

class Scheduler:
    def __init__(self,num_workers=cpu_count()-1):
        self.used_jids = []
        self.jobs = {}            # dictionary of Popen Object for issued jobs, (cmd,inst_num) for queud jobs
        self.events = {}
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
        self.events[new_jid] = threading.Event()
        self.events[new_jid].clear()
        logging.debug(f'jid={new_jid} : Queued "{args}"')
        return new_jid

    def join(self,jid,postexec_fn):
        self.events[jid].wait()

        # subprocess scheduled
        job = self.jobs[jid]
        job.wait()

        # subprocess completed
        ret_code = job.returncode
        
        if ret_code is None:
            return None
        elif ret_code == 0: # process exit normally
            self.lock.acquire()
            self.used_jids.remove(jid)
            self.jobs.pop(jid)
            self.events.pop(jid)
            self.running -= 1
            self.lock.release()

            logging.debug(f'jid={jid} : Returned 0')
            return postexec_fn(job.communicate()[0].decode('utf-8')) # decode stdout
        else:  # FIXME : post-mortem, what is left to do?
            #print('sth unexpected')
            logging.error(f'jid={jid} : Returned {ret_code}')
            exit()

    def schedule(self): # pick jobs from queud jobs to schedule
        if self.running == self.num_workers:
            return

        # CRITICAL: race condition possible
        self.lock.acquire()
        pending_jobs = [(jid,self.jobs[jid][0],self.jobs[jid][1],self.jobs[jid][2],self.jobs[jid][3]) for jid in list(self.jobs.keys()) if type(self.jobs[jid]) is tuple]
        self.lock.release()
        if not len(pending_jobs):
            return

        pending_jobs.sort(key=lambda e:e[1] if type(e[1]) is int else np.inf) # sort by inst number
        
        # TODO: is it better to have self.queue queue into a sorted list, then self.schedule just to simply pop one everytime?
        # we won't want to schedule to much at once, because we might have a VERY long queue of pending jobs, which by the time we are going through all sorted pending jobs, have varied a lot
        scheduled_counter = 0
        
        while len(pending_jobs) and scheduled_counter < self.num_workers: # schedule one-by-one until workers are fed (or out of jobs)
            if self.running == self.num_workers:
                break

            jid, inst_num, cmd, cwd, env = pending_jobs[0]
            
            self.lock.acquire()
            self.running += 1
            self.jobs[jid] = subprocess.Popen(cmd.split(),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            self.lock.release()
           
            self.events[jid].set()
            scheduled_counter += 1
            
            logging.debug(f'jid={jid} : Scheduled' + f' for thread {inst_num}' if inst_num is not None else '')
            #print(f'Scheduled job for thread {inst_num}')
            pending_jobs.pop(0)
