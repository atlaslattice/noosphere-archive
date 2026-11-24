"""Synthetic review of House-only bootstrap under globally shared challenge shocks.
Not an audit of another person's exact data; tests one possible violating structure.
"""
import random,statistics

def bootstrap_interval(house_means,seed=1,draws=499):
    rng=random.Random(seed); n=len(house_means)
    sims=sorted(sum(house_means[rng.randrange(n)] for _ in range(n))/n for _ in range(draws))
    return sims[int((draws-1)*.025)],sims[int((draws-1)*.975)]

def experiment(reps=200,seed=1405):
    rng=random.Random(seed); false_positive=0; examples=[]
    for rep in range(reps):
        # Null effect, but each synthetic scenario set shares one global shock.
        global_shock=rng.gauss(0,.006)
        house_means=[global_shock+rng.gauss(0,.001) for _ in range(12)]
        lo,hi=bootstrap_interval(house_means,seed=seed+rep)
        if lo>0 or hi<0:
            false_positive+=1
            if len(examples)<2:examples.append({'replicate':rep,'globalShock':round(global_shock,6),'houseOnly95Percent':[round(lo,6),round(hi,6)]})
    return {'replicates':reps,'nullEffect':0,'houseOnlyFalseExclusionOfZero':false_positive,
            'examples':examples,'conclusion':'House-only resampling is anti-conservative if global scenario seeds induce shared House shocks; independently re-seed and resample challenge blocks.'}

if __name__=='__main__':
    import json;print(json.dumps(experiment(),indent=2))
