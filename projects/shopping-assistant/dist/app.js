import {products,evaluate} from './engine.js';
const el=id=>document.getElementById(id);
for(const product of products){const o=document.createElement('option');o.value=product.id;o.textContent=`${product.id} · ${product.name}`;el('product').append(o);}
function render(){
  el('error').textContent='';
  try {
    const r=evaluate(el('product').value,el('activity').value,Number(el('hours').value));
    el('context').textContent=`${r.product.id} / ${r.product.name} · ${r.activity} · ${r.hours} hours`;
    el('status').textContent=r.status;el('answer').textContent=r.answer;
    el('counts').textContent=`${r.relevant.length} matching reviews · ${r.positive} positive · ${r.negative} negative`;
    el('caveat').textContent=r.caveat;el('claim').textContent=`${r.product.claim} [${r.product.id}-SPEC]`;
    el('sources').replaceChildren();
    if(!r.relevant.length){const p=document.createElement('p');p.textContent='No matching customer evidence. The manufacturer claim cannot fill that gap.';el('sources').append(p);}
    for(const source of r.relevant){const article=document.createElement('article');const label=document.createElement('p');label.className='source-label';label.textContent=`[${source.id}] · ${source.activity} · ${source.hours} hours · ${source.sentiment}`;const quote=document.createElement('blockquote');quote.textContent=source.text;article.append(label,quote);el('sources').append(article);}
    el('excluded').textContent=`${r.product.reviews.length-r.relevant.length} reviews excluded for activity or duration mismatch. Reviews from other products never enter this answer.`;
  } catch(error){el('error').textContent=error.message;}
}
el('question').addEventListener('submit',event=>{event.preventDefault();render();});render();
