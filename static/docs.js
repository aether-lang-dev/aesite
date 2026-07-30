/* Docs search (client-side over /search.json) + on-page TOC scroll-spy. */
(function(){
  "use strict";
  var input=document.getElementById("ds"), res=document.getElementById("dsres");
  var data=null, items=[], sel=-1;

  function esc(s){return s.replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
  function mark(text,q){
    var i=text.toLowerCase().indexOf(q); if(i<0) return esc(text);
    return esc(text.slice(0,i))+"<b>"+esc(text.slice(i,i+q.length))+"</b>"+esc(text.slice(i+q.length));
  }
  function snippet(text,q){
    var i=text.toLowerCase().indexOf(q); if(i<0) return "";
    var a=Math.max(0,i-32), s=(a>0?"…":"")+text.slice(a,i+q.length+48)+"…";
    return mark(s,q);
  }
  function load(cb){
    if(data){cb();return;}
    fetch("/search.json").then(function(r){return r.json();}).then(function(d){data=d;cb();}).catch(function(){data=[];cb();});
  }
  function search(q){
    q=q.trim().toLowerCase(); if(!q){close();return;}
    var terms=q.split(/\s+/), out=[];
    data.forEach(function(d){
      var sc=0, t=d.title.toLowerCase(), hitH=null, hitS="";
      terms.forEach(function(tm){
        if(t.indexOf(tm)>=0) sc+=60; if(t.indexOf(tm)===0) sc+=30;
        for(var k=0;k<d.headings.length;k++){ if(d.headings[k].text.toLowerCase().indexOf(tm)>=0){sc+=18; if(!hitH)hitH=d.headings[k]; break;} }
        var ti=d.text.toLowerCase().indexOf(tm); if(ti>=0){sc+=6; if(!hitS)hitS=snippet(d.text,tm);}
      });
      if(sc>0){
        var url="/Docs/"+d.slug+".html"+(hitH?("#"+hitH.id):"");
        var label=hitH?(d.title+" › "+hitH.text):d.title;
        out.push({sc:sc,url:url,title:d.title,group:d.group,label:label,snip:hitS,q:terms[0]});
      }
    });
    out.sort(function(a,b){return b.sc-a.sc;});
    render(out.slice(0,8),terms[0]);
  }
  function render(list,q){
    items=list; sel=-1;
    if(!list.length){res.innerHTML='<div class="none">no matches</div>';res.classList.add("open");return;}
    res.innerHTML=list.map(function(r){
      return '<a href="'+r.url+'" role="option"><span class="rt">'+mark(r.title,q)+'<span class="rg">'+esc(r.group)+'</span></span>'+
             (r.snip?'<div class="rs">'+r.snip+'</div>':'')+'</a>';
    }).join("");
    res.classList.add("open");
  }
  function close(){res.classList.remove("open");res.innerHTML="";sel=-1;}
  function move(d){
    var as=res.querySelectorAll("a"); if(!as.length)return;
    sel=(sel+d+as.length)%as.length;
    as.forEach(function(a,i){a.classList.toggle("sel",i===sel);});
    as[sel].scrollIntoView({block:"nearest"});
  }

  if(input){
    input.addEventListener("input",function(){load(function(){search(input.value);});});
    input.addEventListener("focus",function(){if(input.value)load(function(){search(input.value);});});
    input.addEventListener("keydown",function(e){
      if(e.key==="ArrowDown"){e.preventDefault();move(1);}
      else if(e.key==="ArrowUp"){e.preventDefault();move(-1);}
      else if(e.key==="Enter"){var a=res.querySelectorAll("a")[sel<0?0:sel]; if(a){location.href=a.getAttribute("href");}}
      else if(e.key==="Escape"){input.blur();close();}
    });
    document.addEventListener("keydown",function(e){
      if(e.key==="/"&&document.activeElement!==input&&!/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)){e.preventDefault();input.focus();}
    });
    document.addEventListener("click",function(e){if(!e.target.closest(".docsearch"))close();});
  }

  // TOC scroll-spy
  var tocLinks={}; [].forEach.call(document.querySelectorAll(".toc a"),function(a){tocLinks[a.dataset.id]=a;});
  var heads=document.querySelectorAll(".doc-body h2[id], .doc-body h3[id]");
  if(heads.length && window.IntersectionObserver){
    var seen={};
    var obs=new IntersectionObserver(function(es){
      es.forEach(function(e){seen[e.target.id]=e.isIntersecting?e.boundingClientRect.top:null;});
      var best=null;
      [].forEach.call(heads,function(h){ var r=h.getBoundingClientRect(); if(r.top<140) best=h.id; });
      if(best){ for(var k in tocLinks)tocLinks[k].classList.remove("on"); if(tocLinks[best])tocLinks[best].classList.add("on"); }
    },{rootMargin:"-80px 0px -70% 0px",threshold:0});
    [].forEach.call(heads,function(h){obs.observe(h);});
  }
})();
