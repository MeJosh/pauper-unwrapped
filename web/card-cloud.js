function renderCardCloud(cloudCards,limit,container,detail,images){
 const escapeHtml=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ordered=[...cloudCards].sort((a,b)=>b.copies-a.copies||a.card.localeCompare(b.card));
 const selected=limit==='all'?ordered:ordered.slice(0,Number(limit));
 detail.textContent=selected.length?`Showing ${selected.length} of ${ordered.length} matching cards, sized by total copies.`:'No cards found.';
 if(!selected.length){container.innerHTML='<p class="empty">No cards found.</p>';return;}
 const width=Math.max(200,Math.floor(container.getBoundingClientRect().width)-34);
 const gap=3, maxCopies=selected[0].copies;
 const targetHeight=Math.max(300,width*.62);
 const copyUnits=selected.reduce((sum,c)=>sum+c.copies/maxCopies,0);
 // Fit the whole selection into a compact landscape cloud with one shared scale.
 const maxWidth=Math.min(180,width*.4,Math.sqrt(width*targetHeight*.72/(copyUnits*680/488)));
 const cards=selected.map(c=>{
  const imageWidth=maxWidth*Math.sqrt(c.copies/maxCopies);
  return {...c,imageWidth,imageHeight:imageWidth*680/488,w:imageWidth+gap,h:imageWidth*680/488+gap};
 });
 const placed=[];
 for(const card of cards){
  const candidates=[];
  const add=(x,y)=>{
   if(x < -width/2||x+card.w > width/2)return;
   const cx=x+card.w/2,cy=y+card.h/2;
   candidates.push({x,y,score:(cx/width)**2+(cy/targetHeight)**2});
  };
  if(!placed.length)add(-card.w/2,-card.h/2);
  for(const p of placed){
   // Try flush against each edge, aligned at either end or the middle.
   for(const y of [p.y,p.y+p.h-card.h,p.y+(p.h-card.h)/2]){
    add(p.x-card.w,y);add(p.x+p.w,y);
   }
   for(const x of [p.x,p.x+p.w-card.w,p.x+(p.w-card.w)/2]){
    add(x,p.y-card.h);add(x,p.y+p.h);
   }
  }
  candidates.sort((a,b)=>a.score-b.score||a.y-b.y||a.x-b.x);
  const position=candidates.find(({x,y})=>placed.every(p=>
   x+card.w<=p.x+.001||x>=p.x+p.w-.001||y+card.h<=p.y+.001||y>=p.y+p.h-.001));
  // A centered row below the cluster is always available if no edge fits.
  placed.push({...card,...(position||{x:-card.w/2,y:Math.max(0,...placed.map(p=>p.y+p.h))})});
 }
 const top=Math.min(...placed.map(p=>p.y))-8;
 const bottom=Math.max(...placed.map(p=>p.y+p.h))+8;
 container.innerHTML=`<div class="cloud-layout" style="height:${bottom-top}px" role="group" aria-label="Card images sized by total copies">${placed.map((c,i)=>{
  const image=images[c.card];
  const link=image?image.scryfall:'https://scryfall.com/search?q='+encodeURIComponent('!"'+c.card+'"');
  return `<a class="cloud-card" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer" style="left:${c.x+width/2+gap/2}px;top:${c.y-top+gap/2}px;width:${c.imageWidth}px;height:${c.imageHeight}px" data-cloud-index="${i}" aria-label="${escapeHtml(c.card)}: ${c.copies} copies in ${c.decks} decks. Open on Scryfall." title="${escapeHtml(c.card)} · ${c.copies} copies · ${c.decks} decks"><span class="card-image-fallback" aria-hidden="true">${escapeHtml(c.card)}<small>Image unavailable</small></span>${image?`<img src="${escapeHtml(image.image)}" alt="${escapeHtml(c.card)}" width="488" height="680" loading="lazy" decoding="async">`:''}<span class="cloud-copy-count" aria-hidden="true">${c.copies}</span></a>`;
 }).join('')}</div>`;
 container.querySelectorAll('img').forEach(image=>image.addEventListener('error',()=>{image.hidden=true;}));
 container.querySelectorAll('[data-cloud-index]').forEach(word=>{
  const show=()=>{const c=placed[Number(word.dataset.cloudIndex)];detail.textContent=`${c.card} · ${c.copies} total copies · ${c.decks} decks`;};
  word.addEventListener('pointerenter',show);
  word.addEventListener('focus',show);
  word.addEventListener('click',show);
 });
}
