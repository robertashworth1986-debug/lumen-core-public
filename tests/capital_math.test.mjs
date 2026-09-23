import test from 'node:test';
import assert from 'node:assert/strict';
import {nonnegative,runway,fundingGap,dilution,debtPayment} from '../dashboard/js/capital_math.js';

test('missing or invalid inputs cannot silently become a zero-dollar assumption',()=>{
  for(const value of ['', '  ',null,undefined,-1,'invalid',Infinity,NaN])assert.equal(nonnegative(value),null);
  assert.equal(nonnegative('0'),0);
  assert.equal(runway('',5000),null);
  assert.equal(fundingGap(25000,5000,12,'',0),null);
  assert.equal(dilution(100000,0),null);
  assert.equal(debtPayment(50000,10,0),null);
  assert.equal(debtPayment(50000,10,60.5),null);
  assert.equal(debtPayment(50000,-1,60),null);
});
test('constant-burn runway and funding gap retain zero-burn and fully-funded cases',()=>{
  assert.equal(runway(25000,5000),5);
  assert.equal(runway(0,5000),0);
  assert.equal(runway(25000,0),Infinity);
  assert.equal(fundingGap(25000,5000,12,10000,2500),47500);
  assert.equal(fundingGap(100000,5000,12,10000,2500),0);
});
test('priced-round ownership uses post-money denominator and includes no implied valuation',()=>{
  assert.equal(dilution(100000,900000),.1);
  assert.equal(dilution(0,900000),0);
  assert.equal(dilution(900000,900000),.5);
});
test('loan payment matches an independent amortization balance and zero-rate limit',()=>{
  const payment=debtPayment(50000,10,60);
  assert.ok(Math.abs(payment-1062.352235)<.000001);
  let balance=50000;
  for(let month=0;month<60;month++)balance=balance*(1+10/1200)-payment;
  assert.ok(Math.abs(balance)<.000001);
  assert.equal(debtPayment(12000,0,12),1000);
  assert.ok(Math.abs(debtPayment(12000,1e-12,12)-1000)<1e-8);
  assert.equal(debtPayment(0,10,60),0);
});
