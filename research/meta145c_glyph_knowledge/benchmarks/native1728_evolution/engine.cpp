// Direct, bounded synthetic workload transitions. No source text, models or I/O
// beyond the caller-provided integer calibration and the JSON result stream.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <omp.h>

namespace lh {
constexpr int N=1728, K=12, WORDS=27;
constexpr int BASELINE=143; // Current build: one worker, 2048 memo entries, width400.
constexpr std::array<int,12> CAPS={1,2,4,8,16,32,64,128,256,512,1024,2048};
constexpr std::array<int,12> BATCH={1,2,4,8,16,32,64,96,128,192,256,400};
enum Metric {REQUESTS,FRESH,HELD,HITS,MISSES,CHANGES,GLOBAL,OBJECTS,SERVICE,REQUIRED,HELD_COST,VIOLATIONS};
struct Metrics {
 std::array<uint64_t,K> v{};
 void add(const Metrics& other){for(int i=0;i<K;++i)v[i]+=other.v[i];}
};
using Bits=std::array<uint64_t,WORDS>;
int covered(const Bits& a){int n=0;for(auto x:a)n+=__builtin_popcountll(x);return n;}
void merge_bits(Bits& a,const Bits& b){for(int i=0;i<WORDS;++i)a[i]|=b[i];}
uint64_t mix(uint64_t z){z+=0x9e3779b97f4a7c15ULL;z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);}
struct Calibration {uint64_t lookup,store,fixed,item,base;std::array<uint64_t,N> cpu;};
struct Event {int node;bool local,global,unavailable;uint64_t budget;};
std::vector<Event> events(int epoch,int years,uint64_t seed,const Calibration& c){
 std::vector<Event> out;out.reserve(years);
 int regime=epoch%12;int offset=int(mix(seed^uint64_t(epoch))%N);
 const int hotsets[12]={12,144,1728,1728,48,512,144,512,144,1728,144,512};
 for(int y=0;y<years;++y){
  uint64_t r=mix(seed^(uint64_t(epoch)*0xd1342543de82ef95ULL)^uint64_t(y));
  int node=(offset+int(r%hotsets[regime]))%N;
  if(regime==3)node=y%N;
  if(regime==4)node=(offset+(y/12)%48)%N;
  bool local=regime==6&&(y%8==0);
  bool global=(y==0)||(regime==7&&y%64==0)||(regime==11&&y%16==0);
  bool unavailable=regime==10&&r%32==0;
  uint64_t budget=c.base*2;
  if(regime==8)budget=std::max<uint64_t>(1,c.base*2/5);
  if(regime==9)budget=c.base*8;
  out.push_back({node,local,global,unavailable,budget});
 }
 return out;
}
// One live record per stable node key. Explicit dependency invalidation removes
// that key on a supplemental revision; no revision can be served as current.
struct Lru {
 std::array<int,N> prev{},next{};
 std::array<uint32_t,N> current{},stored{};
 std::array<bool,N> present{};
 int first=-1,last=-1,size=0,capacity;
 explicit Lru(int cap):capacity(cap){}
 void clear(){present.fill(false);first=last=-1;size=0;}
 void erase(int n){
  if(!present[n])return;
  if(prev[n]>=0)next[prev[n]]=next[n];else first=next[n];
  if(next[n]>=0)prev[next[n]]=prev[n];else last=prev[n];
  present[n]=false;--size;
 }
 void touch(int n){
  if(present[n])erase(n);
  else if(size==capacity)erase(first);
  prev[n]=last;next[n]=-1;
  if(last>=0)next[last]=n;else first=n;
  last=n;present[n]=true;stored[n]=current[n];++size;
 }
};
struct Result {Metrics metrics;Bits coverage{};uint64_t checksum=1469598103934665603ULL;};
Result simulate(int config,const std::vector<Event>& work,const Calibration& c,std::array<Metrics,N>* nodes=nullptr){
 Lru cache(CAPS[(config/12)%12]);int chunk=BATCH[config%12];
 Result result;uint64_t tokens=work.empty()?0:work[0].budget*2;
 for(const auto& e:work){
  Metrics m;int n=e.node;m.v[REQUESTS]=1;
  if(e.global){
   cache.clear();m.v[GLOBAL]=1;m.v[CHANGES]=1;m.v[OBJECTS]=N;
   uint64_t catalog=c.fixed*((N+chunk-1)/chunk)+c.item*N;
   m.v[SERVICE]+=catalog;m.v[REQUIRED]+=catalog;
  }
  if(e.local){++cache.current[n];cache.erase(n);++m.v[CHANGES];}
  tokens=std::min(tokens+e.budget,e.budget*8);
  bool hit=cache.present[n];
  if(hit&&cache.stored[n]!=cache.current[n]){++m.v[VIOLATIONS];hit=false;}
  uint64_t cost=c.lookup+(hit?0:c.cpu[n]+c.store+c.fixed+c.item);
  m.v[REQUIRED]+=cost;
  bool accepted=!e.unavailable&&tokens>=cost;
  if(accepted){
   tokens-=cost;cache.touch(n);m.v[FRESH]=1;m.v[hit?HITS:MISSES]=1;
   m.v[OBJECTS]+=!hit;m.v[SERVICE]+=cost;
   result.coverage[n/64]|=uint64_t(1)<<(n%64);
  }else{m.v[HELD]=1;m.v[HELD_COST]=cost;}
  result.metrics.add(m);if(nodes)(*nodes)[n].add(m);
  uint64_t tag=uint64_t(n)*257+(accepted?1:0)+(hit?2:0)+(e.local?4:0)+(e.global?8:0)+(e.unavailable?16:0);
  result.checksum=(result.checksum^tag)*1099511628211ULL;
 }
 return result;
}
struct Row {int index;Metrics train,holdout;Bits trainCoverage{},holdoutCoverage{};uint64_t checksum=0;};
bool better(const Metrics& a,int ac,const Metrics& b,int bc,int ai,int bi){
 if(a.v[VIOLATIONS]!=b.v[VIOLATIONS])return a.v[VIOLATIONS]<b.v[VIOLATIONS];
 if(ac!=bc)return ac>bc;
 if(a.v[FRESH]!=b.v[FRESH])return a.v[FRESH]>b.v[FRESH];
 if(a.v[HELD]!=b.v[HELD])return a.v[HELD]<b.v[HELD];
 if(a.v[SERVICE]!=b.v[SERVICE])return a.v[SERVICE]<b.v[SERVICE];
 return ai<bi; // index order: workers, capacity, chunk, all ascending.
}
struct Epoch {int epoch,split,winner,incumbent;bool accepted;uint64_t checksum;};
void metric_json(const Metrics& m){std::cout<<'[';for(int i=0;i<K;++i){if(i)std::cout<<',';std::cout<<m.v[i];}std::cout<<']';}
void hex_json(uint64_t x){std::ostringstream s;s<<std::hex<<std::setfill('0')<<std::setw(16)<<x;std::cout<<'"'<<s.str()<<'"';}
int run(){
 int epochs,years,threads,count,audit;uint64_t seed;
 if(!(std::cin>>epochs>>years>>threads>>seed>>count>>audit))throw std::runtime_error("INPUT_HEADER");
 if(epochs<1||epochs>1729||years<1||years>1728||threads<1||threads>4||count<1||count>N||(audit!=0&&audit!=1))throw std::runtime_error("INPUT_BOUND");
 std::vector<int> indices(count);std::array<bool,N> seen{};
 for(auto& i:indices){if(!(std::cin>>i)||i<0||i>=N||seen[i])throw std::runtime_error("CONFIG_INDEX");seen[i]=true;}
 Calibration c{};
 if(!(std::cin>>c.lookup>>c.store>>c.fixed>>c.item))throw std::runtime_error("CALIBRATION");
 for(auto& cost:c.cpu)if(!(std::cin>>cost)||cost==0||cost>1000000000ULL)throw std::runtime_error("CPU_COST");
 if(c.lookup>1000000000ULL||c.store>1000000000ULL||c.fixed>1000000000ULL||c.item>1000000000ULL)throw std::runtime_error("CALIBRATION_BOUND");
 auto sorted=c.cpu;std::sort(sorted.begin(),sorted.end());
 c.base=c.lookup+c.store+c.fixed+c.item+sorted[N/2];
 if(c.base==0)throw std::runtime_error("ZERO_BASE");
 std::vector<Row> rows;for(int i:indices){Row row{};row.index=i;rows.push_back(row);}
 std::vector<Epoch> synthesis;std::vector<Result> batch(count);
 int incumbent=-1,selected=-1;uint64_t evaluated=0;
 auto start=std::chrono::steady_clock::now();omp_set_num_threads(threads);
 for(int e=0;e<epochs;++e){
  auto work=events(e,years,seed,c);bool holdout=(e/12)%4==3;
  #pragma omp parallel for schedule(static)
  for(int r=0;r<count;++r)batch[r]=simulate(rows[r].index,work,c);
  int epochWinner=-1;
  for(int r=0;r<count;++r){
   auto& row=rows[r];auto& result=batch[r];evaluated+=result.metrics.v[REQUESTS];
   if(holdout){row.holdout.add(result.metrics);merge_bits(row.holdoutCoverage,result.coverage);}
   else{
    row.train.add(result.metrics);merge_bits(row.trainCoverage,result.coverage);
    if(epochWinner<0||better(result.metrics,covered(result.coverage),batch[epochWinner].metrics,covered(batch[epochWinner].coverage),row.index,rows[epochWinner].index))epochWinner=r;
   }
   row.checksum=mix(row.checksum^result.checksum^uint64_t(e));
  }
  if(!holdout){
   selected=0;
   for(int r=1;r<count;++r)if(better(rows[r].train,covered(rows[r].trainCoverage),rows[selected].train,covered(rows[selected].trainCoverage),rows[r].index,rows[selected].index))selected=r;
  }
  bool changed=!holdout&&incumbent!=rows[selected].index;
  if(!holdout)incumbent=rows[selected].index;
  synthesis.push_back({e,int(holdout),epochWinner<0?-1:rows[epochWinner].index,incumbent,changed,rows[selected].checksum});
  if(e%144==143)std::cerr<<"completed_epochs="<<(e+1)<<" evaluated_updates="<<evaluated<<'\n';
 }
 auto coreEnd=std::chrono::steady_clock::now();
 std::array<Metrics,N> baselineNodes{},selectedNodes{};
 std::array<Metrics,12> baselineRegimes{},selectedRegimes{};
 std::array<Metrics,12> baselineTrainRegimes{},selectedTrainRegimes{};
 uint64_t auditUpdates=0;Metrics baselineAudit,selectedAudit;
 if(audit){
  for(int e=0;e<epochs;++e){
   auto work=events(e,years,seed,c);
   auto b=simulate(BASELINE,work,c,&baselineNodes),s=simulate(rows[selected].index,work,c,&selectedNodes);
   baselineAudit.add(b.metrics);selectedAudit.add(s.metrics);
   baselineRegimes[e%12].add(b.metrics);selectedRegimes[e%12].add(s.metrics);
   if((e/12)%4!=3){baselineTrainRegimes[e%12].add(b.metrics);selectedTrainRegimes[e%12].add(s.metrics);}
   auditUpdates+=b.metrics.v[REQUESTS]+s.metrics.v[REQUESTS];
  }
 }
 auto end=std::chrono::steady_clock::now();
 std::cout<<"{\"engineVersion\":1,\"evaluatedUpdates\":"<<evaluated<<",\"auditReplayUpdates\":"<<auditUpdates;
 std::cout<<",\"elapsedNs\":"<<std::chrono::duration_cast<std::chrono::nanoseconds>(end-start).count();
 std::cout<<",\"coreElapsedNs\":"<<std::chrono::duration_cast<std::chrono::nanoseconds>(coreEnd-start).count();
 std::cout<<",\"selectedIndex\":"<<rows[selected].index<<",\"rows\":[";
 for(int r=0;r<count;++r){
  if(r)std::cout<<',';auto& row=rows[r];std::cout<<"{\"index\":"<<row.index<<",\"train\":";metric_json(row.train);
  std::cout<<",\"holdout\":";metric_json(row.holdout);std::cout<<",\"coverage\":["<<covered(row.trainCoverage)<<','<<covered(row.holdoutCoverage)<<"],\"checksum\":";hex_json(row.checksum);std::cout<<'}';
 }
 std::cout<<"],\"epochs\":[";
 for(size_t i=0;i<synthesis.size();++i){if(i)std::cout<<',';auto& e=synthesis[i];std::cout<<'['<<e.epoch<<','<<e.split<<','<<e.winner<<','<<e.incumbent<<','<<e.accepted<<',';hex_json(e.checksum);std::cout<<']';}
 std::cout<<"],\"audit\":{\"baseline\":";metric_json(baselineAudit);std::cout<<",\"selected\":";metric_json(selectedAudit);
 std::cout<<",\"nodes\":[";
 if(audit)for(int i=0;i<N;++i){if(i)std::cout<<',';std::cout<<'[';metric_json(baselineNodes[i]);std::cout<<',';metric_json(selectedNodes[i]);std::cout<<']';}
 std::cout<<"],\"regimes\":[";
 if(audit)for(int i=0;i<12;++i){if(i)std::cout<<',';std::cout<<'[';metric_json(baselineRegimes[i]);std::cout<<',';metric_json(selectedRegimes[i]);std::cout<<']';}
 std::cout<<"],\"trainRegimes\":[";
 if(audit)for(int i=0;i<12;++i){if(i)std::cout<<',';std::cout<<'[';metric_json(baselineTrainRegimes[i]);std::cout<<',';metric_json(selectedTrainRegimes[i]);std::cout<<']';}
 std::cout<<"]}}\n";return 0;
}
}
int main(){try{return lh::run();}catch(const std::exception& e){std::cerr<<"LONG_HORIZON_ENGINE_ERROR:"<<e.what()<<'\n';return 2;}}
