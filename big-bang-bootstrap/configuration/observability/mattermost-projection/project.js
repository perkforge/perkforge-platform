// Fixed audience projection: never forward Helm messages, annotations or metadata.
import fs from 'fs';
import crypto from 'crypto';
function project(event, route) {
    if (!event || typeof event !== 'object' || !event.involvedObject) throw Error('event');
    const obj = event.involvedObject;
    if (obj.kind !== 'HelmRelease' || !['helm.toolkit.fluxcd.io/v2', 'helm.toolkit.fluxcd.io/v2beta2'].includes(obj.apiVersion)) throw Error('kind');
    const source = obj.namespace + '/' + obj.name;
    if (!route.sources.includes(source)) throw Error('source');
    const match = typeof event.message === 'string' && event.message.match(/^Helm (install|upgrade) (succeeded|failed) for release /);
    if (!match || event.severity !== (match[2] === 'failed' ? 'error' : 'info')) throw Error('outcome');
    return {text: route.title + ': Helm ' + match[1] + ' ' + match[2] + '.\nRelease: ' + source + '\n' + route.link};
}
function equal(a,b) {
    const x=crypto.createHash('sha256').update(a).digest('hex');
    const y=crypto.createHash('sha256').update(b).digest('hex');
    let diff=0; for(let i=0;i<x.length;i++) diff |= x.charCodeAt(i)^y.charCodeAt(i); return diff===0;
}
async function receive(r) {
    if (r.method !== 'POST') { r.return(405); return; }
    try {
        const config=JSON.parse(fs.readFileSync('/run/projection/routes.json','utf8'));
        const route=config[r.uri];
        if (!route || r.variables.args || !equal(r.headersIn.Authorization || '', 'Bearer '+route.token)) { r.return(403); return; }
        if (!/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]+)?\/hooks\/[a-z0-9]{26}$/.test(route.hook)) throw Error('configuration');
        const payload=project(JSON.parse(r.requestText),route);
        const result=await ngx.fetch(route.hook, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),verify:true,max_response_body_size:1024});
        if (result.status!==200 || (await result.text()).trim()!=='ok') {r.return(502,'Delivery failed');return;}
        r.return(200,'Delivered');
    } catch(e) {r.return(400,'Invalid event or delivery failure');}
}
export default {receive,project};
