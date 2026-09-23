// Planning calculations. No account data, rates, valuation or eligibility is inferred.
export function nonnegative(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? n : null;
}
export function runway(cash, burn) {
  cash=nonnegative(cash); burn=nonnegative(burn);
  if(cash===null||burn===null) return null;
  return burn===0 ? Infinity : cash/burn;
}
export function fundingGap(cash,burn,months,oneoff,fees) {
  const v=[cash,burn,months,oneoff,fees].map(nonnegative);
  if(v.includes(null))return null;
  return Math.max(0,v[1]*v[2]+v[3]+v[4]-v[0]);
}
export function dilution(raise,premoney) {
  raise=nonnegative(raise); premoney=nonnegative(premoney);
  if(raise===null||premoney===null||premoney<=0)return null;
  return raise/(premoney+raise);
}
export function debtPayment(principal,annualPercent,months) {
  principal=nonnegative(principal); annualPercent=nonnegative(annualPercent); months=nonnegative(months);
  if(principal===null||annualPercent===null||months===null||months<=0||!Number.isInteger(months)||annualPercent>100)return null;
  const r=annualPercent/1200;
  // log1p/expm1 avoid cancellation at very small, nonzero interest rates.
  return r===0?principal/months:principal*r/-Math.expm1(-months*Math.log1p(r));
}
