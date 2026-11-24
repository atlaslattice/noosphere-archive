"""Peer #118 follow-up: independent synthetic null worlds with AR(1) challenge shocks.
Compares naive IID challenge bootstrap versus moving-block time bootstrap.
This tests an assumption, not other authors' unpublished experiment or real agent quality.
"""
import json,numpy as np

def interval(samples):
    return np.percentile(samples,[2.5,97.5])

def run_null_experiment(*,worlds=150,reps=299,timesteps=432,house_count=12,rho=.94,block=48,seed=4117):
    rng=np.random.default_rng(seed)
    iid_fail=block_fail=0;examples=[]
    for trial in range(worlds):
        sd=.006; g=np.empty(timesteps);g[0]=rng.normal(0,sd)
        innovations=rng.normal(0,sd*np.sqrt(1-rho*rho),size=timesteps)
        for t in range(1,timesteps):g[t]=rho*g[t-1]+innovations[t]
        # 12 Houses share each world shock. A zero-mean treatment difference is known by construction.
        d=g[None,:]+rng.normal(0,.001,size=(house_count,timesteps))
        by_time=d.mean(axis=0)
        iid=by_time[rng.integers(0,timesteps,size=(reps,timesteps))].mean(axis=1)
        blocks=(timesteps+block-1)//block
        starts=rng.integers(0,timesteps,size=(reps,blocks,1))
        indices=(starts+np.arange(block))%timesteps
        index=indices.reshape((reps,-1))[:,:timesteps]
        mb=by_time[index].mean(axis=1)
        il,iu=interval(iid);bl,bu=interval(mb)
        ai=il>0 or iu<0;ab=bl>0 or bu<0
        iid_fail+=int(ai);block_fail+=int(ab)
        if len(examples)<3 and ai and not ab:
            examples.append({'trial':trial,'timeSeriesMean':float(by_time.mean()),'iidCI':[float(il),float(iu)],'movingBlockCI':[float(bl),float(bu)]})
    return {'syntheticNullWorlds':worlds,'trueEffect':0,'rho':rho,'blockLength':block,'iidTimeCIExcludesZero':iid_fail,
            'movingBlockCIExcludesZero':block_fail,'examples':examples,'interpretation':
            'IID time resampling ignores temporal correlation. Moving-block controls some but may not fully calibrate; must choose block length using independent source/time dependence. No hosted model inference.'}

if __name__=='__main__':print(json.dumps(run_null_experiment(),indent=2))
