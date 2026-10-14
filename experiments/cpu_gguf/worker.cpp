#include "llama.h"
#include "nlohmann/json.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using json = nlohmann::json;
static void quiet(ggml_log_level level, const char *text, void *) {
    if (level >= GGML_LOG_LEVEL_ERROR) std::cerr << text;
}
int main(int argc,char **argv) {
    if(argc!=4){std::cerr<<"usage: worker model.gguf embeddings|generate threads\n";return 2;}
    llama_log_set(quiet,nullptr);llama_backend_init();
    auto mp=llama_model_default_params();mp.n_gpu_layers=0;
    auto *model=llama_model_load_from_file(argv[1],mp);
    if(!model){std::cerr<<"model load failed\n";return 1;}
    bool embeddings=std::string(argv[2])=="embeddings";
    auto cp=llama_context_default_params();
    cp.n_ctx=4096;cp.n_batch=4096;cp.n_ubatch=512;
    cp.n_threads=cp.n_threads_batch=std::stoi(argv[3]);
    cp.embeddings=embeddings;cp.pooling_type=LLAMA_POOLING_TYPE_NONE;
    cp.attention_type=LLAMA_ATTENTION_TYPE_CAUSAL;
    cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;
    cp.offload_kqv=false;cp.op_offload=false;
    cp.type_k=cp.type_v=GGML_TYPE_F32;
    auto *ctx=llama_init_from_model(model,cp);
    if(!ctx){llama_model_free(model);return 1;}
    auto *vocab=llama_model_get_vocab(model);
    const int dim=llama_model_n_embd(model);
    std::cout<<json({{"ready",true},{"cpu_only",true},{"hidden_size",dim}}).dump()<<std::endl;
    std::string line;
    while(std::getline(std::cin,line)){
      try{
        auto request=json::parse(line);
        if(request.contains("tokenize")){
          auto text=request["tokenize"].get<std::string>();
          int n=-llama_tokenize(vocab,text.data(),text.size(),nullptr,0,request.value("add_special",false),true);
          std::vector<llama_token> ids(n);
          n=llama_tokenize(vocab,text.data(),text.size(),ids.data(),ids.size(),request.value("add_special",false),true);
          if(n<0)throw std::runtime_error("tokenization failed");ids.resize(n);
          std::cout<<json({{"ids",ids}}).dump()<<std::endl;continue;
        }
        auto ids=request.at("ids").get<std::vector<llama_token>>();
        int max_new=request.value("max_new_tokens",192);
        if(ids.empty()||ids.size()+(embeddings?0:max_new)>4096)throw std::runtime_error("context limit");
        const int vocab_size=llama_vocab_n_tokens(vocab);
        for(auto id:ids)if(id<0||id>=vocab_size)throw std::runtime_error("invalid token ID");
        auto positions=request.value("positions",std::vector<int>{});
        for(int p:positions)if(p<0||p>=int(ids.size()))throw std::runtime_error("invalid readout position");
        llama_memory_clear(llama_get_memory(ctx),true);
        auto start=std::chrono::steady_clock::now();
        auto batch=llama_batch_init(ids.size(),0,1);batch.n_tokens=ids.size();
        for(int i=0;i<int(ids.size());i++){
          batch.token[i]=ids[i];batch.pos[i]=i;batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;
          batch.logits[i]=embeddings?(std::find(positions.begin(),positions.end(),i)!=positions.end()):(i==int(ids.size())-1);
        }
        int rc=llama_decode(ctx,batch);llama_batch_free(batch);
        if(rc)throw std::runtime_error("prompt decode failed: "+std::to_string(rc));
        double prefill=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        json result;
        if(embeddings){
          result["hidden"]=json::array();
          for(int p:positions){auto *h=llama_get_embeddings_ith(ctx,p);if(!h)throw std::runtime_error("missing embedding");result["hidden"].push_back(std::vector<float>(h,h+dim));}
        }else{
          std::vector<llama_token> output;bool stopped=false;
          auto *sampler=llama_sampler_init_greedy();
          for(int j=0;j<max_new;j++){
            auto token=llama_sampler_sample(sampler,ctx,-1);output.push_back(token);
            if(llama_vocab_is_eog(vocab,token)){stopped=true;break;}
            if(j+1==max_new)break;
            auto b=llama_batch_init(1,0,1);b.n_tokens=1;b.token[0]=token;b.pos[0]=ids.size()+j;b.n_seq_id[0]=1;b.seq_id[0][0]=0;b.logits[0]=1;
            rc=llama_decode(ctx,b);llama_batch_free(b);
            if(rc){llama_sampler_free(sampler);throw std::runtime_error("generation decode failed");}
          }
          llama_sampler_free(sampler);result["ids"]=output;result["truncated"]=!stopped;
        }
        result["prefill_ms"]=prefill;
        result["elapsed_ms"]=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        std::cout<<result.dump()<<std::endl;
      }catch(const std::exception &e){std::cout<<json({{"error",e.what()}}).dump()<<std::endl;}
    }
    llama_free(ctx);llama_model_free(model);llama_backend_free();return 0;
}
