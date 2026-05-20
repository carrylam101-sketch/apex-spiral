// APEX V10.3 Gini Gene Selector — Rust
// Gini=1-Σp_k², ΔGini, H=-Σp_klog₂p_k, IG, Bootstrap~63.2%, OOB~36.8%
// © 2026 璇玑帝国
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
pub fn gini_impurity(labels: &[bool]) -> f64 {
    if labels.is_empty() { return 0.0; }
    let n=labels.len() as f64; let pt=labels.iter().filter(|&&x|x).count() as f64/n;
    1.0-(pt*pt+(1.0-pt)*(1.0-pt))
}
pub fn gini_gain(parent: &[bool], splits: &[Vec<bool>]) -> f64 {
    let n=parent.len() as f64; if n==0.0{return 0.0;}
    let pg=gini_impurity(parent); let mut wg=0.0;
    for c in splits{let w=c.len() as f64/n; wg+=w*gini_impurity(c);}
    (pg-wg).max(0.0)
}
pub fn entropy(labels: &[bool]) -> f64 {
    if labels.is_empty(){return 0.0;}
    let n=labels.len() as f64; let pt=labels.iter().filter(|&&x|x).count() as f64/n;
    let pf=1.0-pt; let mut h=0.0;
    if pt>0.0{h-=pt*pt.log2();} if pf>0.0{h-=pf*pf.log2();} h.max(0.0)
}
pub fn information_gain(parent: &[bool], splits: &[Vec<bool>]) -> f64 {
    let n=parent.len() as f64; if n==0.0{return 0.0;}
    let pe=entropy(parent); let mut we=0.0;
    for c in splits{let w=c.len() as f64/n; we+=w*entropy(c);}
    (pe-we).max(0.0)
}
struct LcgRng{u:u64}
impl LcgRng{fn new(s:u64)->Self{LcgRng{u:s}} fn n(&mut self)->u64{self.u=self.u.wrapping_mul(6364136223846793005).wrapping_add(1);self.u}}
pub fn bootstrap_indices(n:usize,seed:u64)->(Vec<usize>,Vec<usize>){
    let mut r=LcgRng::new(seed); let tot=((n as f64)*0.632)as usize;
    let mut s:HashSet<usize>=HashSet::new();
    while s.len()<tot{s.insert((r.n()as usize)%n);}
    let b:Vec<usize>=s.iter().copied().collect();
    let o:Vec<usize>=(0..n).filter(|i|!s.contains(i)).collect();(b,o)
}
#[derive(Debug,Clone,Serialize,Deserialize)]pub struct GeneCandidate{
    pub id:String,pub name:String,pub category:String,
    pub n_signals:usize,pub usage_count:usize,pub success_rate:f64,
}
#[derive(Debug,Clone,Serialize,Deserialize)]pub struct ForestResult{
    pub selected_gene_id:String,pub votes:HashMap<String,u32>,pub n_trees:usize,
    pub gini_gain:f64,pub ig_gain:f64,pub oob_accuracy:f64,pub combined_score:f64,
}
pub struct GiniGeneSelector{n_trees:usize,seed:u64}
impl GiniGeneSelector{pub fn new(n:usize,s:u64)->Self{GiniGeneSelector{n_trees:n,seed:s}}
    fn ev(&self,g:&GeneCandidate,o:&[bool])->f64{
        let t=o.iter().filter(|&&x|x).count(); let l:Vec<bool>=o.iter().take(t).copied().collect();
        let r:Vec<bool>=o.iter().skip(t).copied().collect();
        gini_gain(o,&[l.clone(),r.clone()])*0.4+information_gain(o,&[l,r])*0.3+g.success_rate*0.3
    }
    fn boot<'a>(&self,gs:&'a[GeneCandidate],s:u64)->Vec<&'a GeneCandidate>{
        let n=gs.len();if n==0{return vec![];}
        let sz=((n as f64)*0.632)as usize; let mut r=LcgRng::new(s); let mut h:HashSet<usize>=HashSet::new(); let mut o:Vec<&GeneCandidate>=vec![];
        while o.len()<sz{let i=(r.n()as usize)%n;if h.insert(i){o.push(&gs[i]);}} o
    }
    pub fn select(&self,gs:&[GeneCandidate],o:&[bool])->ForestResult{
        if gs.is_empty(){return ForestResult{selected_gene_id:"null".into(),votes:HashMap::new(),n_trees:0,gini_gain:0.0,ig_gain:0.0,oob_accuracy:0.0,combined_score:0.0};}
        let mut vo:HashMap<String,u32>=HashMap::new(); let mut gs2=0.0;let mut is=0.0;let mut os=0.0;let mut vk=0;
        for t in 0..self.n_trees{
            let b=self.boot(gs,self.seed.wrapping_add(t as u64));
            if b.len()<2{continue;}
            let mut bi=b[0].id.clone();let mut bs=-1.0;
            for g in &b{let sc=self.ev(g,o);if sc>bs{bs=sc;bi=g.id.clone();}}
            *vo.entry(bi).or_insert(0)+=1;
            if let Some(g)=gs.iter().find(|x|x.id==bi){let e=self.ev(g,o);gs2+=gini_gain(o,&[o.iter().filter(|&&x|x).copied().collect(),o.iter().filter(|&&x|!x).copied().collect()]);is+=information_gain(o,&[o.iter().filter(|&&x|x).copied().collect(),o.iter().filter(|&&x|!x).copied().collect()]);os+=g.success_rate;vk+=1;}
        }
        let nv=vk.max(1)as f64;
        let sid=vo.iter().max_by_key(|(_,v)|*v).map(|(k,_)|k.clone()).unwrap_or_else(||gs[0].id.clone());
        ForestResult{selected_gene_id:sid,votes:vo,n_trees:self.n_trees,gini_gain:gs2/nv,ig_gain:is/nv,oob_accuracy:os/nv,combined_score:(gs2/nv)*0.4+(is/nv)*0.3+(os/nv)*0.3}
    }
}
#[cfg(test)]mod t{use super::*;
    #[test]fn tg(){assert!((gini_impurity(&[true,true])-0.0).abs()<1e-6);}
    #[test]fn tg2(){assert!((gini_impurity(&[true,false])-0.5).abs()<1e-6);}
    #[test]fn tg3(){let v=gini_impurity(&[true,true,true,false]);assert!((v-0.375).abs()<1e-5);}
    #[test]fn te(){assert!((entropy(&[true,false])-1.0).abs()<1e-6);}
    #[test]fn tb(){let(b,o)=bootstrap_indices(100,42);assert!(!b.is_empty());assert_eq!(b.len()+o.len(),100);}
    #[test]fn ts(){let gs=vec![GeneCandidate{id:"g1".into(),name:"n".into(),category:"r".into(),n_signals:5,usage_count:10,success_rate:0.8},GeneCandidate{id:"g2".into(),name:"n".into(),category:"i".into(),n_signals:3,usage_count:5,success_rate:0.6}];let o=vec![true,true,false,false,true];let r=GiniGeneSelector::new(5,12345).select(&gs,&o);assert!(!r.selected_gene_id.is_empty());}
}
