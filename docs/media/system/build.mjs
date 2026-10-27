// SPDX-License-Identifier: Apache-2.0
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as k from './vendor/iso-kit.mjs';
import { concept, plans, partGroups, partCount } from './model.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const W = 1120, H = 750;
const P = k.fitProjection([
  ...k.boxCorners(plans.mat, -2, 3),
  ...k.boxCorners(plans.screen, 12, 112),
], 1040, 465, { pad: 25, azimuth: 55, elevation: 33 });
P.origin[0] += 40;
P.origin[1] += 110;
const at = p => k.iso(p, P);
const S = k.solidSvg, L = k.lineSvg;
const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const parts = [];
const expected = new Set(Object.values(partGroups).flat());
function put(name, center, svg, group) {
  if (!expected.delete(name)) throw new Error(`Unexpected or duplicate part: ${name}`);
  parts.push({ name, center, svg, group, depth: k.depthOf(center, P) });
}
function slab(name, plan, z, h, { material = '', tone = 'mid', extra = '', group = 'computer', bevel = .6 } = {}) {
  put(name, [plan.x + plan.w / 2, plan.y + plan.d / 2, z + h / 2],
    S(k.slabOf(plan, z, h, P, 7, bevel), { tone, crease: 'faint', className: material }) + extra, group);
}
const outline = (plan, z, tone = 'faint') => L(k.planOutline(plan, z, P), { tone });
const printed = (a, b, z, tone = 'lo') => L(k.lineOnTop(a, b, z, P), { tone, free: true });
const dot = (p, r = .65, color = '#7c8773') => { const [x,y] = at(p); return `<circle cx="${x}" cy="${y}" r="${r}" fill="${color}"/>`; };
function faceRect(x, z, w, h, y, radius = 0, cls = '') {
  const d = k.pathOf(k.roundedPlan({ x, y: z, w, d: h, r: radius }, 8).map(([a,b]) => at([a,y,b])), true);
  return `<path class="${cls}" d="${d}"/>`;
}
const faceText = (x,z,y,text,size=4.2,cls='ui-text') =>
  `<g transform="${k.sideMatrix([0,y],0,P,'left')}"><text x="${x}" y="${-z}" font-size="${size}" class="${cls}">${esc(text)}</text></g>`;

// 01. Two real, layered desk-mat parts. The mat is a shared workspace, not a data bus.
slab('felt underside', plans.mat, -1.5, 2, { material:'felt', tone:'lo', group:'workspace', bevel:0 });
slab('work mat', k.insetPlan(plans.mat, .9), .5, 2.6, { material:'mat', tone:'lo', group:'workspace',
  extra: outline(k.insetPlan(plans.mat, 6),3.1,'faint') });

// 02. Ordinary personal computer. Nothing here depicts a dedicated EgoBase appliance.
slab('lower chassis', plans.laptop, 3.1, 6, { material:'metal', tone:'mid',
  extra:L(k.sideSeam(plans.laptop,5.4,P,7),{tone:'faint'}) });
slab('keyboard deck', k.insetPlan(plans.laptop,1.2), 9.1, 1.5, { material:'metal', tone:'mid' });
for (const [name,x] of [['left hinge',-45],['right hinge',56]])
  slab(name,{x,y:-35,w:14,d:6,r:1.2},10.6,3.2,{material:'dark',tone:'lo'});
slab('display housing',plans.screen,12,100,{material:'dark',tone:'hi',bevel:1});
put('display bezel',[12,-33.8,61],faceRect(-58,15,140,94,-33.8,3,'screen-bezel'),'computer');
const glass = faceRect(-54,21,132,83,-33.6,1.8,'screen-glass');
let ui = '';
ui += faceRect(-49,92,21,6,-33.5,1,'ui-brand');
ui += faceText(-46,94,-33.45,'DATA CORE',3.0,'ui-text ui-brand-text');
ui += faceText(-49,82,-33.45,'EVIDENCE',3.0,'ui-muted');
ui += faceText(5,82,-33.45,'CONTEXT',3.0,'ui-muted');
for (let i=0;i<3;i++) {
  ui += faceRect(-49,62-i*13,45,15,-33.5,1.2,'ui-card');
  ui += faceRect(-45,70-i*13,4,4,-33.4,.5,'ui-icon');
  ui += faceRect(-37,71-i*13,26-i*3,1.3,-33.4,.3,'ui-rule');
  ui += faceRect(-37,67-i*13,18+i*2,1,-33.4,.3,'ui-faint');
}
ui += faceRect(4,44,67,33,-33.5,1.2,'ui-card');
for(let i=0;i<4;i++) ui += faceRect(9,69-i*5,51-[5,0,11,3][i],1.2,-33.4,.3,i===0?'ui-rule':'ui-faint');
ui += faceText(6,34,-33.45,'Your decision',3.7,'ui-text');
ui += faceRect(39,26,32,11,-33.45,1.5,'authorize');
ui += faceText(44,30,-33.4,'AUTHORIZE',3.5,'ui-text authorization-text');
put('display glass',[12,-33.5,62],glass + `<clipPath id="screen-clip">${faceRect(-54,21,132,83,-33.5,1.8)}</clipPath><g clip-path="url(#screen-clip)">${ui}</g>`,'computer');

slab('keyboard recess',{x:-51,y:-20,w:126,d:51,r:2.5},10.6,.3,{material:'recess',tone:'lo',bevel:0});
let keyId=0;
for(let row=0;row<3;row++) for(let col=0;col<9;col++) {
  const x=-48+col*13.25, y=-16+row*11.7;
  const p={x,y,w:10.8,d:9.1,r:1.1};
  const mark=printed([x+3,y+3.5],[x+5.5,y+3.5],12.7,'lo');
  slab(`keycap ${String(++keyId).padStart(2,'0')}`,p,10.9,1.8,{material:'keys',tone:'lo',extra:mark,group:'keys',bevel:.35});
}
for(const p of [{x:-48,y:19,w:18,d:8.2,r:1.1},{x:-27,y:19,w:67,d:8.2,r:1.1},{x:43,y:19,w:25.8,d:8.2,r:1.1}])
  slab(`keycap ${String(++keyId).padStart(2,'0')}`,p,10.9,1.8,{material:'keys',tone:'lo',group:'keys',bevel:.35});
slab('trackpad recess',{x:-18,y:38,w:60,d:24,r:2},10.6,.2,{material:'recess',tone:'lo',bevel:0});
slab('trackpad',{x:-17.3,y:38.7,w:58.6,d:22.6,r:1.5},10.8,.15,{material:'metal',tone:'lo',bevel:0});
for(const [name,x] of [['left speaker grille',-57],['right speaker grille',78]]) {
  let perforations='';
  for(let j=0;j<15;j++) for(let i=0;i<2;i++) perforations+=dot([x+.9+i*1.6,-14+j*2.5,11.05],.28,'#7a8177');
  slab(name,{x,y:-16,w:3.4,d:39,r:1.2},10.6,.3,{material:'metal',tone:'lo',extra:perforations,bevel:0});
}
slab('front opening notch',{x:0,y:67,w:25,d:1.5,r:.6},7.9,1.4,{material:'recess',tone:'lo',bevel:0});

// 03. An explicitly generic exposed observation board, not a finished EgoLink shell.
slab('board support',{x:-154,y:17,w:65,d:80,r:4},3.1,1.7,{material:'paper',tone:'lo',group:'observations'});
let boardDetails='';
for(const [x,y] of k.corners(plans.board,4)) boardDetails+=outline({x:x-1.2,y:y-1.2,w:2.4,d:2.4,r:1},6.4,'mid');
for(const x of [-146,-99]) for(let j=0;j<10;j++) boardDetails+=dot([x,35+j*4.8,6.5],.65,'#a4ac9c');
slab('exposed circuit board',plans.board,4.8,1.6,{material:'pcb',tone:'hi',group:'observations',extra:boardDetails});
slab('controller package',{x:-138,y:48,w:21,d:23,r:1},6.4,3,{material:'dark',tone:'hi',group:'observations',
  extra:printed([-134,56],[-122,56],9.4,'lo')+printed([-134,60],[-126,60],9.4,'lo')});
slab('radio shield',{x:-139,y:26,w:29,d:17,r:1},6.4,5,{material:'metal',tone:'mid',group:'observations',
  extra:outline({x:-137,y:28,w:25,d:13,r:.8},11.4,'faint')});
slab('antenna zone',{x:-108,y:25,w:11,d:19,r:.5},6.4,.3,{material:'pcb-pale',tone:'lo',group:'observations',bevel:0,
  extra:outline({x:-105,y:28,w:5,d:13,r:.4},6.7,'lo')});
slab('USB connector',{x:-132,y:89,w:17,d:8,r:1.2},6.4,5.2,{material:'metal',tone:'mid',group:'observations',
  extra:outline({x:-129,y:93,w:11,d:2.5,r:.7},11.6,'mid')});
slab('button body',{x:-113,y:74,w:10,d:10,r:1},6.4,2,{material:'dark',tone:'lo',group:'observations'});
slab('button cap',{x:-111,y:76,w:6,d:6,r:1.1},8.4,1.6,{material:'metal',tone:'mid',group:'observations'});
slab('sensor package',{x:-112,y:52,w:9,d:9,r:.7},6.4,2.5,{material:'dark',tone:'lo',group:'observations'});
for(const [name,x] of [['header rail one',-150],['header rail two',-96]]) {
  let pins='';
  for(let j=0;j<7;j++) pins+=outline({x:x+.8,y:49+j*4.3,w:1.8,d:1.8,r:.25},9.8,'hi');
  slab(name,{x,y:47,w:3.4,d:31.5,r:.6},6.4,3.4,{material:'dark',tone:'lo',group:'observations',extra:pins});
}
slab('passive one',{x:-139,y:77,w:6,d:3,r:.4},6.4,1.3,{material:'metal',tone:'lo',group:'observations'});
slab('passive two',{x:-129,y:77,w:6,d:3,r:.4},6.4,1.3,{material:'metal',tone:'lo',group:'observations'});

// 04. A real shallow paper tray. Cards stand for traceable records, not digital hardware.
slab('tray base',plans.tray,3.1,2.6,{material:'tray',tone:'mid',group:'evidence'});
slab('tray rear wall',{x:106,y:10,w:54,d:2.4,r:.5},5.7,8,{material:'tray',tone:'mid',group:'evidence'});
slab('tray side wall',{x:157.6,y:12.4,w:2.4,d:71.2,r:.5},5.7,8,{material:'tray',tone:'mid',group:'evidence'});
slab('tray front lip',{x:106,y:83.6,w:54,d:2.4,r:.5},5.7,4,{material:'tray',tone:'mid',group:'evidence'});
slab('archive card',{x:111,y:16,w:40,d:62,r:1.5},5.7,.7,{material:'paper',tone:'lo',group:'evidence',
  extra:outline({x:115,y:20,w:31,d:18,r:1},6.4,'faint')});
const receipt={x:114,y:29,w:36,d:47,r:1};
let receiptPrint=outline({x:118,y:34,w:7,d:7,r:1},7.2,'mid');
for(let j=0;j<6;j++) receiptPrint+=printed([118,46+j*4],[143-(j%3)*3,46+j*4],7.2,j===0?'mid':'lo');
slab('source receipt',receipt,6.4,.8,{material:'paper',tone:'mid',group:'evidence',extra:receiptPrint});
slab('receipt retaining clip',{x:125,y:26,w:15,d:5,r:.8},7.2,2.5,{material:'metal',tone:'mid',group:'evidence',
  extra:outline({x:128,y:27.3,w:9,d:2.2,r:.6},9.7,'lo')});

if(expected.size) throw new Error(`Parts not drawn: ${[...expected].join(', ')}`);
// Foundations must precede the parts they support. A single centre-depth sort
// cannot order a large desk mat or a chassis against all smaller attached parts.
const groupOrder = {workspace:0,computer:1,keys:2,observations:3,evidence:4};
parts.sort((a,b)=>groupOrder[a.group]-groupOrder[b.group]);
const css = `
.iso[data-theme="light"]{--anatomy-paper:#f5f7ef;--anatomy-top:#f7f8f2;--anatomy-face:#fff;
--anatomy-shade-0:#b5bead;--anatomy-shade-1:#c9d0c1;--anatomy-shade-2:#dce1d5;--anatomy-shade-3:#ebeee4;
--anatomy-hi:#353c30;--anatomy-mid:#7e8776;--anatomy-lo:#a5ae9c;--anatomy-faint:#cbd2c2;
--anatomy-dot:#5c6853;--anatomy-weight:.72px;--anatomy-halo:#79806e;--anatomy-halo-opacity:.15}
.mat{--anatomy-top:#e9ede2;--anatomy-shade-0:#bdc6b0;--anatomy-shade-1:#ced6c4;--anatomy-shade-2:#dae1d1;--anatomy-shade-3:#e1e7d9}
.felt{--anatomy-top:#c9d1bf;--anatomy-shade-0:#b0baa4;--anatomy-shade-1:#bec8b1;--anatomy-shade-2:#c8d1bc;--anatomy-shade-3:#d1d8c6}
.metal{--anatomy-top:#f2f4ed;--anatomy-shade-0:#aeb6a5;--anatomy-shade-1:#c3cbbb;--anatomy-shade-2:#d5dccd;--anatomy-shade-3:#e6eadf}
.dark{--anatomy-paper:#20271d;--anatomy-top:#343e2d;--anatomy-shade-0:#151a12;--anatomy-shade-1:#1d2419;--anatomy-shade-2:#293222;--anatomy-shade-3:#303b29;--anatomy-hi:#323e29;--anatomy-faint:#57624c;--anatomy-lo:#536147}
.recess{--anatomy-top:#b6c0ab;--anatomy-shade-0:#7c8770;--anatomy-shade-1:#919d85;--anatomy-shade-2:#a4af99;--anatomy-shade-3:#b1bda4}
.keys{--anatomy-top:#f9fbf5;--anatomy-shade-0:#b2bda7;--anatomy-shade-1:#cad3c0;--anatomy-shade-2:#e0e6d9;--anatomy-shade-3:#eef2e8}
.paper{--anatomy-top:#fffef8;--anatomy-shade-0:#d3d6c9;--anatomy-shade-1:#e0e3d6;--anatomy-shade-2:#edf0e5;--anatomy-shade-3:#f6f8ee}
.pcb{--anatomy-top:#626f58;--anatomy-shade-0:#3d4a34;--anatomy-shade-1:#47553d;--anatomy-shade-2:#536249;--anatomy-shade-3:#657358;--anatomy-hi:#4b5b3e;--anatomy-mid:#96a18b;--anatomy-faint:#89967b}
.pcb-pale{--anatomy-top:#8b9a7d;--anatomy-lo:#b5c1a9}
.tray{--anatomy-top:#d4ddc8;--anatomy-shade-0:#939f86;--anatomy-shade-1:#a9b49b;--anatomy-shade-2:#bdc8b0;--anatomy-shade-3:#cbd5bf}
.screen-bezel{fill:#182014;stroke:#65705c;stroke-width:.7}
.screen-glass{fill:#edf1e5;stroke:#8b987e;stroke-width:.6}
.ui-brand{fill:#d8e0cd}.ui-text{fill:#30392a;font-family:Arial,sans-serif;font-weight:600}
.ui-muted{fill:#78856b;font-family:Arial,sans-serif;letter-spacing:.5px}.ui-card{fill:#fcfdf7;stroke:#d1dac7;stroke-width:.4}
.ui-icon{fill:#c7d1bb}.ui-rule{fill:#9fac91}.ui-faint{fill:#d0dac5}.authorize{fill:#b4ff5a;stroke:#6cae20;stroke-width:.5}
.ui-brand-text{fill:#627055}.authorization-text{fill:#334c1c;font-weight:700}
.title{font:600 31px Arial,sans-serif;letter-spacing:-.5px;fill:#111410}
.eyebrow{font:600 14px Arial,sans-serif;letter-spacing:2px;fill:#6a7660}
.label{font:600 21px Arial,sans-serif;fill:#273020}.sub{font:16px Arial,sans-serif;fill:#77836b}
.note{font:16px Arial,sans-serif;fill:#59664d}.small{font:13px Arial,sans-serif;fill:#77836b}
`;
const scene=parts.map(p=>`<g data-part="${p.name}" data-group="${p.group}">${p.svg}</g>`).join('');
const caption = [
  `<text x="48" y="635" class="label">EgoLink</text><text x="48" y="661" class="sub">Physical observations</text><text x="48" y="686" class="small">ENGINEERING PROTOTYPE</text>`,
  `<text x="405" y="635" class="label">EgoBase / Data Core</text><text x="405" y="661" class="sub">Evidence + personal context</text><text x="405" y="686" class="small">SOFTWARE PROTOTYPE ON A PC</text>`,
  `<text x="800" y="635" class="label">You remain in control</text><text x="800" y="661" class="sub">Review, then authorize</text><text x="800" y="686" class="small">PRODUCT DIRECTION</text>`,
].join('');
const body = `<style>${css}</style><rect width="${W}" height="${H}" rx="18" fill="#f5f7ef"/>
<rect x=".6" y=".6" width="${W-1.2}" height="${H-1.2}" rx="18" fill="none" stroke="#d8dfcf"/>
<path d="M48 37h20v13h-7v7H48Z" fill="#96cf53"/><text x="79" y="52" class="eyebrow">EGO / SYSTEM CONCEPT</text>
<text x="48" y="93" class="title">${concept.title}</text><text x="1072" y="92" text-anchor="end" class="small">FIG. 01</text>
<path class="iso-halo" d="${k.haloOf(plans.mat,-2,5,P)}"/>${scene}
<path d="M48 604H1072" stroke="#d6decc" stroke-width="1"/>
${caption}<text x="48" y="727" class="note">Concept only · ${esc(concept.integration.label)}</text>`;
const svg = k.figureSvg({width:W,height:H,label:'Product-direction concept: an exposed EgoLink prototype board, a personal computer running a conceptual Data Core interface, and evidence cards. The complete Link-to-Base integration is not yet complete.',body,standalone:'light'});
writeFileSync(join(HERE,'ego-system.svg'),svg+'\n');
if (process.argv.includes('--preview')) writeFileSync(join(HERE,'preview.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ego system concept</title><style>body{margin:0;background:#e9ede3;padding:24px;box-sizing:border-box}main{max-width:1120px;margin:0 auto}svg{display:block;width:100%;height:auto}@media(max-width:500px){body{padding:8px}}</style><main>${svg}</main></html>`);
writeFileSync(join(HERE,'parts.json'),JSON.stringify({concept,physicalParts:partCount,groups:partGroups,painterOrder:parts.map(({name,group,depth})=>({name,group,depth:Number(depth.toFixed(3))}))},null,2)+'\n');
console.log(`Built ego-system.svg: ${partCount} physical parts, no invented performance or completed integration.`);
