export const products = [
  {id:'AB-123', name:'Shift Walker', claim:'Advertised as offering all-day comfort.', reviews:[
    {id:'AB-R1', activity:'standing', hours:8, sentiment:'positive', text:'Comfortable through my eight-hour shop shift.'},
    {id:'AB-R2', activity:'standing', hours:8, sentiment:'negative', text:'My feet hurt after six hours standing at work.'},
    {id:'AB-R3', activity:'desk', hours:8, sentiment:'positive', text:'Comfortable at my desk all day.'},
    {id:'AB-R4', activity:'standing', hours:4, sentiment:'positive', text:'Comfortable for a four-hour standing shift.'}
  ]},
  {id:'CD-456', name:'Everyday Cushioned', claim:'Advertised with a cushioned footbed.', reviews:[
    {id:'CD-R1', activity:'standing', hours:8, sentiment:'positive', text:'Comfortable during eight hours at the counter.'},
    {id:'CD-R2', activity:'standing', hours:9, sentiment:'positive', text:'Comfortable through my nine-hour standing shift.'},
    {id:'CD-R3', activity:'standing', hours:8, sentiment:'negative', text:'Heel pain after an eight-hour standing shift.'},
    {id:'CD-R4', activity:'walking', hours:2, sentiment:'positive', text:'Comfortable during a two-hour walk.'}
  ]},
  {id:'EF-789', name:'New Arrival', claim:'Advertised as providing all-day comfort.', reviews:[]}
];

export function evaluate(productId, activity, hours) {
  const product = products.find(p=>p.id===productId);
  if (!product) throw new Error('Select a product from the catalog.');
  if (!['standing','desk','walking'].includes(activity) || !Number.isFinite(hours) || hours<1 || hours>16) {
    throw new Error('Choose an activity and a duration between 1 and 16 hours.');
  }
  // Product identity is a hard filter. Rating and sentiment never affect ranking.
  const ranked = product.reviews.filter(r=>r.activity===activity)
    .map(r=>({...r, durationGap:Math.abs(r.hours-hours)}))
    .sort((a,b)=>a.durationGap-b.durationGap || a.id.localeCompare(b.id));
  // A deliberately simple teaching rule, not a scientifically validated threshold.
  const relevant = ranked.filter(r=>r.durationGap<=1);
  const positive = relevant.filter(r=>r.sentiment==='positive').length;
  const negative = relevant.filter(r=>r.sentiment==='negative').length;
  let status, answer;
  if (!relevant.length) {
    status='Insufficient evidence';
    answer='There are no reviews matching this activity within one hour of your intended duration. I cannot establish comfort for this use.';
  } else if (positive && negative) {
    status='Conflicting experiences';
    answer=positive===negative
      ? 'The matching reviews are evenly split between positive and negative comfort experiences.'
      : `Most matching reviews report ${positive>negative?'positive':'negative'} comfort experiences, but there is conflicting evidence.`;
  } else {
    status='Limited customer evidence';
    answer=`The ${relevant.length===1?'matching review reports':'matching reviews report'} ${positive?'positive':'negative'} comfort experiences. This small sample does not establish how the shoes will feel for you.`;
  }
  return {product, activity, hours, ranked, relevant, positive, negative, status, answer,
    caveat:'These are fictional sample reviews, not a representative customer survey. Review proportions are not your probability of comfort.'};
}
