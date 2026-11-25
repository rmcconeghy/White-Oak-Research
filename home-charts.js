/* Homepage-only responsive views. Read canonical data and geometry; never mutate analysis assets. */
const NS = "http://www.w3.org/2000/svg";
const svgEl = (tag, attrs={}, text) => {
  const node = document.createElementNS(NS, tag);
  for (const [k,v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  if (text !== undefined) node.textContent = text;
  return node;
};
const getText = async path => {
  const response = await fetch(new URL(path, import.meta.url));
  if (!response.ok) throw new Error(path + ": " + response.status);
  return response.text();
};
const series = [
  ["private","Private insurance","--chart-private"],
  ["medicare","Medicare","--chart-medicare"],
  ["medicaid","Medicaid","--chart-medicaid"],
  ["out_of_pocket","Out-of-pocket","--chart-pocket"],
  ["other","Other NHE","--chart-other"]
];
const trillions = number => "$" + number.toFixed(2) + "T";
function drawSpending(host, rows) {
  const w = Math.floor(host.clientWidth), h = Math.floor(host.clientHeight);
  if (w < 100 || h < 100) return;
  const svg = svgEl("svg",{viewBox:"0 0 "+w+" "+h,"aria-hidden":"true"});
  const left=34, right=w-(w>=620?178:112), top=13, bottom=h-25;
  const x=i=>left+(right-left)*i/(rows.length-1);
  const y=v=>bottom-(bottom-top)*v/6;
  const text=(x,y,t,attrs={})=>svg.append(svgEl("text",{x,y,fill:"var(--muted)","font-size":12,...attrs},t));
  const line=(x1,y1,x2,y2,attrs={})=>svg.append(svgEl("line",{x1,y1,x2,y2,stroke:"var(--chart-grid)",...attrs}));
  for (const tick of [0,2,4,6]) {
    line(left,y(tick),right,y(tick));
    text(left-5,y(tick)+4,"$"+tick+"T",{"text-anchor":"end"});
  }
  let cumulative=rows.map(()=>0);
  const labels=[];
  for(const [key,name,color] of series){
    const prior=cumulative;
    cumulative=rows.map((row,i)=>prior[i]+row[key]);
    const points=cumulative.map((v,i)=>[x(i),y(v)]).concat(prior.map((v,i)=>[x(i),y(v)]).reverse());
    svg.append(svgEl("polygon",{points:points.map(p=>p.join(",")).join(" "),fill:"var("+color+")",stroke:"var(--chart-water)","stroke-width":0.7}));
    const last=rows.length-1;
    labels.push({name,color,value:rows[last][key],anchor:y((prior[last]+cumulative[last])/2)});
  }
  const yearTicks=w<410?[1996,2010,2024]:[1996,2003,2010,2017,2024];
  for(const year of yearTicks){
    const i=rows.findIndex(row=>row.year===year);
    if(i>=0) text(x(i),h-7,String(year),{"text-anchor":"middle"});
  }
  const last=rows[rows.length-1];
  text(right-4,y(cumulative.at(-1))-7,trillions(last.total)+" total",{"text-anchor":"end","font-weight":700,fill:"var(--ink)"});
  // Direct labels retain the true band midpoint via leaders, even where labels need spacing.
  labels.sort((a,b)=>a.anchor-b.anchor);
  const step=w>=620?21:29, lo=top+7, hi=bottom-9;
  let positions=labels.map((l,i)=>Math.max(l.anchor,lo+i*step));
  for(let i=positions.length-2;i>=0;i--) positions[i]=Math.min(positions[i],positions[i+1]-step);
  const shift=Math.max(0,positions.at(-1)-hi);
  positions=positions.map(p=>p-shift);
  labels.forEach((label,i)=>{
    const p=positions[i], tx=right+12;
    line(right,label.anchor,right+8,p,{stroke:"var("+label.color+")","stroke-width":1.4});
    const attrs={"font-weight":600,fill:"var(--ink)"};
    if(w>=620) text(tx,p+4,label.name+" "+trillions(label.value),attrs);
    else {text(tx,p-2,label.name,attrs);text(tx,p+11,trillions(label.value),{"font-size":12});}
  });
  host.replaceChildren(svg);
}
async function spending(host){
  const csv=await getText("./analyses/us-healthcare-spending/data/payer-mix.csv");
  const [head,...body]=csv.trim().split(/\r?\n/).map(line=>line.split(","));
  const read=(row,key)=>Number(row[head.indexOf(key)]);
  const rows=body.map(row=>({year:read(row,"year"),total:read(row,"nhe_real_2024_usd_millions")/1e6,...Object.fromEntries(series.map(([key])=>[key,read(row,key+"_real_2024_usd_millions")/1e6]))})).filter(row=>row.year>=1996&&row.year<=2024);
  if(rows.length!==29||rows.some(row=>Object.values(row).some(v=>!Number.isFinite(v))))throw new Error("Invalid spending series");
  const resize=()=>drawSpending(host,rows);
  new ResizeObserver(resize).observe(host);
  resize();
}
async function dialysis(host){
  const raw=await getText("./analyses/dialysis-transit/dialysis-access.svg");
  const documentSvg=new DOMParser().parseFromString(raw,"image/svg+xml");
  const source=documentSvg.querySelector('svg svg[viewBox="142 184 560 590"]');
  if(!source)throw new Error("Dialysis map missing");
  const map=document.importNode(source,true);
  for(const a of ["x","y","width","height"])map.removeAttribute(a);
  map.setAttribute("viewBox","195 184 505 470");
  map.setAttribute("aria-hidden","true");
  // Water is the outer tile's surface, not a second poster background.
  map.querySelector(":scope > rect")?.remove();
  const palette={"#dfebeb":"--chart-water","#e8e7dd":"--chart-land","#bbc3ba":"--chart-boundary","#fcfaf0":"--chart-road","#7f9991":"--chart-stop","#70918b":"--chart-stop","#183f3e":"--chart-medicare","#ac4026":"--chart-highlight","#85351f":"--chart-highlight"};
  for(const el of map.querySelectorAll("*")){
    for(const a of ["fill","stroke"]){const v=el.getAttribute(a);if(palette[v])el.setAttribute(a,"var("+palette[v]+")");}
    if(el.tagName.toLowerCase()==="text"){
      el.removeAttribute("font-family");
      el.setAttribute("paint-order","stroke");
      el.setAttribute("stroke","var(--chart-water)");
      el.setAttribute("stroke-width","3");
      if(el.textContent==="Tiverton"){el.setAttribute("x","685");el.setAttribute("y","407");el.setAttribute("text-anchor","end");}
      if(el.textContent==="Westerly"){el.setAttribute("x","266");el.setAttribute("y","580");}
    }
  }
  host.replaceChildren(map);
  const resize=()=>{
    const scale=Math.min(host.clientWidth/505,host.clientHeight/470);
    if(scale>0)for(const label of map.querySelectorAll("text"))label.setAttribute("font-size",Math.max(21,12/scale));
  };
  new ResizeObserver(resize).observe(host);
  resize();
}
for(const host of document.querySelectorAll("[data-chart]")){
  const render=host.dataset.chart==="spending"?spending:dialysis;
  render(host).catch(error=>{
    console.error(error);
    host.replaceChildren(Object.assign(document.createElement("span"),{className:"chart-loading",textContent:"Chart unavailable — open the full analysis."}));
  });
}
