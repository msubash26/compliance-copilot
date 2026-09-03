# Judge calibration worksheet

20 items, 11 of them contested -- the judge and
the mechanical checks reached opposite verdicts. Score each axis yourself **before**
reading the judge's reasoning, then copy your three booleans into the matching line of
`items.jsonl` under `human`. Nothing here changes `golden/v1` (ADR-017).

- **supported** -- is every claim in the answer stated in the clauses below?
- **complete** -- does it cover what the gold clauses state?
- **cited_correctly** -- are the clauses cited the ones the support came from?

## 1. t-002 · plan_and_execute  · **contested**

**Question.** How often should an FMC monitor its managed assets to ensure it stays within specific limits?

**Answer.** An FMC subject to specific limits on managed assets should periodically monitor the size of the assets being managed (Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05], clause 2.3.3).

**Cited.** bbfd16576f29b9c1:2.3.3
**Gold.** bbfd16576f29b9c1:2.3.3

> **Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05] · bbfd16576f29b9c1:2.3.3**
>
> moneys  and  assets  contracted  to  the  FMC,  but  which  have  been  subcontracted to another party and for which the other party is carrying out fund management, whether on a discretionary authority granted by the customer or otherwise.
> 2.4 Exceeding the Limit of Managed Assets - An FMC subject to specific limits on managed assets should periodically monitor the size of the assets being managed, for the purpose of ensuring that it is adhering to such limits. The FMC should, among other things, consider potential changes in the size of the assets being managed arising from prospecting of new investors or investment mandates.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 2. t-002 · supervisor  · **contested**

**Question.** How often should an FMC monitor its managed assets to ensure it stays within specific limits?

**Answer.** An FMC subject to specific limits on managed assets should periodically monitor the size of the assets being managed (Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05], clause 2.3.3).

**Cited.** bbfd16576f29b9c1:2.3.3
**Gold.** bbfd16576f29b9c1:2.3.3

> **Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05] · bbfd16576f29b9c1:2.3.3**
>
> moneys  and  assets  contracted  to  the  FMC,  but  which  have  been  subcontracted to another party and for which the other party is carrying out fund management, whether on a discretionary authority granted by the customer or otherwise.
> 2.4 Exceeding the Limit of Managed Assets - An FMC subject to specific limits on managed assets should periodically monitor the size of the assets being managed, for the purpose of ensuring that it is adhering to such limits. The FMC should, among other things, consider potential changes in the size of the assets being managed arising from prospecting of new investors or investment mandates.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 3. t-005 · plan_and_execute  · **contested**

**Question.** Which specific information sources should be used to screen customers against?

**Answer.** Customers should be screened against relevant money laundering and terrorism financing information sources, as well as lists and information provided by the Authority or other relevant authorities in Singapore, according to Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks, clause 6.39; Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism, clause 6.34; Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees, clause 6.37; and Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs), clause 7.43.

**Cited.** 1b9b9f6db2876069:6.39, 3bd0ff97c75d1a40:6.34, 604c3f4b73b0a8ad:6.37, 61178e1043022702:7.43
**Gold.** 1363829f117073a2:5.1

> **Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · 1b9b9f6db2876069:6.39**
>
> A  bank  shall  screen  a  customer,  natural  persons  appointed  to  act  on  behalf  of  the customer,  connected  parties  of  the  customer  and  beneficial  owners  of  the  customer against relevant money laundering and terrorism financing information sources, as well as  lists  and  information  provided  by  the  Authority  or  other  relevant  authorities  in Singapore for the purposes of determining if there are any money laundering or terrorism financing risks in relation to the customer.

> **Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism · 3bd0ff97c75d1a40:6.34**
>
> The Depository shall screen a customer, natural persons appointed to act on behalf of the customer, connected parties of the customer and beneficial owners of the customer against relevant money laundering and terrorism financing information sources, as well as  lists  and  information  provided  by  the  Authority  or  other  relevant  authorities  in Singapore for the purposes of determining if there are any money laundering or terrorism financing risks in relation to the customer.

> **Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · 604c3f4b73b0a8ad:6.37**
>
> A licensee shall screen a customer, natural persons appointed to act on behalf of the customer, connected parties of the customer and beneficial owners of the customer against relevant money laundering and terrorism financing information sources, as
> well as lists and information provided by the Authority or other relevant authorities in Singapore  for  the  purposes  of  determining  if  there  are  any  money  laundering  or terrorism financing risks in relation to the customer.

> **Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · 61178e1043022702:7.43**
>
> A VCC shall screen a customer, natural persons appointed to act on behalf of the customer, connected parties of the customer and beneficial owners of the customer against relevant money  laundering  and  terrorism  financing  information  sources,  as  well  as  lists  and information  provided  by  the  Authority  or  other  relevant  authorities  in  Singapore  for  the purposes of determining if there are any money laundering or terrorism financing risks in relation to the customer.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 4. t-005 · single_agent  · **contested**

**Question.** Which specific information sources should be used to screen customers against?

**Answer.** Based on the MAS Guidelines on Prevention of Money Laundering and Countering the Financing of Terrorism for Direct General Insurance Business, Reinsurance Business, and Direct Life Insurance Business (Accident & Health Policies), customers should be screened against the following specific information sources:

1. **Lists and information provided by the Authority or other relevant authorities in Singapore** - specifically those related to ML/TF (Money Laundering/Terrorism Financing) risks
2. **The First Schedule of the TSOFA** (Terrorism Suppression Order (Amendment) Act)
3. **The FSM Sanctions Regulations**

These sources contain designated names of individuals and entities that should be screened against when conducting customer due diligence procedures.

Source: Guidelines on Prevention of Money Laundering and Countering the Financing of Terrorism - Direct General Insurance Business, Reinsurance Business, and Direct Life Insurance Business (Accident & Health Policies), doc_id: 1363829f117073a2, section_path: 5.1

**Cited.** 1363829f117073a2:5.1
**Gold.** 1363829f117073a2:5.1

> **Guidelines on Prevention of Money Laundering and Countering the Financing of Terrorism - Direct General Insurance Business, Reinsurance Business, and Direct Life Insurance Business (Accident & Health Policies) · 1363829f117073a2:5.1**
>
> Screening of customers 11  should be carried out against relevant ML/TF information sources, which include designated names of individuals and entities within:
> (a) the lists and information provided by the Authority or other relevant authorities in Singapore in relation to ML/TF risks;
> (b) the First Schedule of the TSOFA; and
> 10 There should minimally be some form of regularity with regard to such training.
> 11
> For the purposes of these Guidelines, the definition of the term 'customers' will vary depending on the type
> of insurance business (e.g. direct insurance business, reinsurance business), and is elaborated on in paragraphs
> 5.2 and 5.3 of these Guidelines.
> (c) the FSM Sanctions Regulations.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 5. t-005 · supervisor  · **contested**

**Question.** Which specific information sources should be used to screen customers against?

**Answer.** Customers should be screened against relevant money laundering and terrorism financing information sources, as well as lists and information provided by the Authority or other relevant authorities in Singapore, according to Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks, clause 6.39; Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism, clause 6.34; Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees, clause 6.37; and Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs), clause 7.43.

**Cited.** 1b9b9f6db2876069:6.39, 3bd0ff97c75d1a40:6.34, 604c3f4b73b0a8ad:6.37, 61178e1043022702:7.43
**Gold.** 1363829f117073a2:5.1

> **Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · 1b9b9f6db2876069:6.39**
>
> A  bank  shall  screen  a  customer,  natural  persons  appointed  to  act  on  behalf  of  the customer,  connected  parties  of  the  customer  and  beneficial  owners  of  the  customer against relevant money laundering and terrorism financing information sources, as well as  lists  and  information  provided  by  the  Authority  or  other  relevant  authorities  in Singapore for the purposes of determining if there are any money laundering or terrorism financing risks in relation to the customer.

> **Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism · 3bd0ff97c75d1a40:6.34**
>
> The Depository shall screen a customer, natural persons appointed to act on behalf of the customer, connected parties of the customer and beneficial owners of the customer against relevant money laundering and terrorism financing information sources, as well as  lists  and  information  provided  by  the  Authority  or  other  relevant  authorities  in Singapore for the purposes of determining if there are any money laundering or terrorism financing risks in relation to the customer.

> **Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · 604c3f4b73b0a8ad:6.37**
>
> A licensee shall screen a customer, natural persons appointed to act on behalf of the customer, connected parties of the customer and beneficial owners of the customer against relevant money laundering and terrorism financing information sources, as
> well as lists and information provided by the Authority or other relevant authorities in Singapore  for  the  purposes  of  determining  if  there  are  any  money  laundering  or terrorism financing risks in relation to the customer.

> **Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · 61178e1043022702:7.43**
>
> A VCC shall screen a customer, natural persons appointed to act on behalf of the customer, connected parties of the customer and beneficial owners of the customer against relevant money  laundering  and  terrorism  financing  information  sources,  as  well  as  lists  and information  provided  by  the  Authority  or  other  relevant  authorities  in  Singapore  for  the purposes of determining if there are any money laundering or terrorism financing risks in relation to the customer.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 6. t-006 · plan_and_execute  · **contested**

**Question.** What information regarding a customer's business relationship must a Commercial Money Institution obtain during the application process?

**Answer.** A Commercial Money Institution must obtain information as to the purpose and intended nature of such account relationship or relevant business transaction (Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals, clause 6.18).

**Cited.** 441e2dd1bba03cbe:6.18
**Gold.** 2b1bc1dfa4766264:6.18

> **Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · 441e2dd1bba03cbe:6.18**
>
> A  financial  institution  shall,  when  processing  the  application  to  establish  an  account relationship,  or  undertaking  a  relevant  business  transaction  without  an  account  being opened, understand and as appropriate, obtain from the customer information as to the purpose  and  intended  nature  of  such  account  relationship  or  relevant  business transaction.
> (VI) Review  of  Relevant  Business  Transactions  Undertaken  without  an  Account  Being Opened

_mechanical:_ `{"success": false, "retrieved_gold": false, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 7. t-006 · supervisor  · **contested**

**Question.** What information regarding a customer's business relationship must a Commercial Money Institution obtain during the application process?

**Answer.** A Commercial Money Institution must obtain information as to the purpose and intended nature of such account relationship or relevant business transaction (Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals, clause 6.18).

**Cited.** 441e2dd1bba03cbe:6.18
**Gold.** 2b1bc1dfa4766264:6.18

> **Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · 441e2dd1bba03cbe:6.18**
>
> A  financial  institution  shall,  when  processing  the  application  to  establish  an  account relationship,  or  undertaking  a  relevant  business  transaction  without  an  account  being opened, understand and as appropriate, obtain from the customer information as to the purpose  and  intended  nature  of  such  account  relationship  or  relevant  business transaction.
> (VI) Review  of  Relevant  Business  Transactions  Undertaken  without  an  Account  Being Opened

_mechanical:_ `{"success": false, "retrieved_gold": false, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 8. t-007 · plan_and_execute  · **contested**

**Question.** What are the experience and qualification requirements for a CEO or an Executive Director?

**Answer.** Based on the provided excerpts:

1. **Insurance Brokers** (Criteria for the Registration of an Insurance Broker [IA/II-G04], clause 4.3):
   - **Experience**: At least 5 years of relevant working experience.
   - **Additional Experience for CEO**: At least 3 years of managerial experience in the relevant field.
   - **Qualifications**: Satisfactory academic and/or professional qualifications.

2. **Digital Token Service Providers** (Guidelines on Licensing for Digital Token Service Providers, clause 3.2.3) and **Payment Service Providers** (Guidelines on Licensing for Payment Service Providers [PS-G01] (w.e.f 8 October 2025), clause 3.1.3):
   - **Experience**: Sufficient experience in operating a business in the specific industry (digital token services or payment services) or related areas in the financial services industry, including sufficient understanding of the regulatory framework.
   - **Additional Experience for Managing Sizeable Teams**: Relevant experience, competencies, and influence to exercise effective oversight and control.
   - **Qualifications**: Educational qualifications and professional certification should be considered.

3. **Fund Management Companies** (Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05], clause 3.7.3):
   - **Experience**: Relevant experience in industry segments within the fund's investment mandate; experience gained at unregulated entities must be substantiated; experience gained more than 10 years ago or with multiple short stints may not be considered relevant.
   - **Qualifications/Competency**: The period of relevant experience is considered in assessing competency. External involvements and conflicts of interest are managed by focusing on FMC business management.

4. **Real Estate Investment Trust Management** (Excerpt [5]):
   - No specific experience or qualification requirements for the CEO are listed; the excerpt focuses on disclosure of remuneration.

**Cited.** f03ab4a4ef9d7b37:4.3, 3a02ac314f68629e:3.2.3, b75f7fa613e6320e:3.1.3, bbfd16576f29b9c1:3.7.3
**Gold.** f03ab4a4ef9d7b37:4.3

> **Criteria for the Registration of an Insurance Broker [IA/II-G04] · f03ab4a4ef9d7b37:4.3**
>
> The  Chief  Executive  Officer  ['CEO']  and  Executive  Directors  ['EDs'] should have at least 5 years of relevant working experience. They should also have satisfactory academic and/or professional qualifications.  In addition, the CEO should have at least 3 years of managerial experience in the relevant field.
> Track Record

> **Guidelines on Licensing for Digital Token Service Providers · 3a02ac314f68629e:3.2.3**
>
> Competency of Key Individuals -  The  applicant  must  ensure that  its soleproprietor, partners, managers or executive directors and CEO have sufficient experience  in  operating  a  business  in  the  digital  token  services  industry, including having  sufficient understanding  of  the regulatory framework for DTSPs in Singapore.
> Where the  individual  will  be  managing  a  sizeable  team,  the  sole-proprietor, partners,  managers  or  executive  directors  and  CEO  should  also  have  the relevant experience, competencies, and influence, to allow them to exercise effective oversight and control over the business activities and staff.
> The  applicant should also consider the educational qualifications and professional certification of its key individuals.

> **Guidelines on Licensing for Payment Service Providers [PS-G01] (w.e.f 8 October 2025) · b75f7fa613e6320e:3.1.3**
>
> Competency of Key Individuals -  The applicant must ensure that its soleproprietor, partners, or executive directors and CEO have sufficient experience in operating a business in the payment services industry or related areas in the financial  services  industry,  including  having  sufficient  understanding  of  the regulatory framework for payment service providers in Singapore.
> Where the  individual  will  be  managing  a  sizeable  team,  the  sole-proprietor, partners,  or  executive  directors  and  CEO  should  also  have  the  relevant experience, competencies, and influence, to allow them to exercise effective oversight and control over the business activities and staff.
> The applicant should also consider the educational qualifications and professional certification of its key individuals.

> **Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05] · bbfd16576f29b9c1:3.7.3**
>
> Private equity and venture capital funds - Relevant experience may include experience  in  industry  segments  that  are  within  the  fund's  investment mandate.
> 3.8 MAS  does  not  consider  e xperience  in  investing  one's own  moneys  or  moneys belonging to family members, as being relevant experience in the context of an FMC that is seeking  to  manage  monies  for  third  parties. Where  an  individual's  past  experience  in investment management was gained at unregulated entities, the FMC must be prepared to substantiate the individual's experience. In addition, the period of relevant experience will be considered in assessing the competency of key individuals. For example, an individual with multiple short stints or with experience gained more than 10 years ago, may not be considered to possess the relevant experience required.
> 3.9 External Involvements of Key Individuals - CEOs and Executive Directors are expected to focus on the management of the FMC's business and may be required to divest outside business interests, if they are unable to adequately mitigate the conflicts of interest (whether actual or perceived), or reputational risks posed to the FMC.
> 3.10 Appointme

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 9. t-007 · supervisor  · **contested**

**Question.** What are the experience and qualification requirements for a CEO or an Executive Director?

**Answer.** Based on the provided excerpts:

1. **Insurance Brokers** (Criteria for the Registration of an Insurance Broker [IA/II-G04], clause 4.3):
   - **Experience**: At least 5 years of relevant working experience.
   - **Additional Experience for CEO**: At least 3 years of managerial experience in the relevant field.
   - **Qualifications**: Satisfactory academic and/or professional qualifications.

2. **Digital Token Service Providers** (Guidelines on Licensing for Digital Token Service Providers, clause 3.2.3) and **Payment Service Providers** (Guidelines on Licensing for Payment Service Providers [PS-G01] (w.e.f 8 October 2025), clause 3.1.3):
   - **Experience**: Sufficient experience in operating a business in the specific industry (digital token services or payment services) or related areas in the financial services industry, including sufficient understanding of the regulatory framework.
   - **Additional Experience for Managing Sizeable Teams**: Relevant experience, competencies, and influence to exercise effective oversight and control.
   - **Qualifications**: Educational qualifications and professional certification should be considered.

3. **Fund Management Companies** (Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05], clause 3.7.3):
   - **Experience**: Relevant experience in industry segments within the fund's investment mandate; experience gained at unregulated entities must be substantiated; experience gained more than 10 years ago or with multiple short stints may not be considered relevant.
   - **Qualifications/Competency**: The period of relevant experience is considered in assessing competency. External involvements and conflicts of interest are managed by focusing on FMC business management.

4. **Real Estate Investment Trust Management** (Excerpt [5]):
   - No specific experience or qualification requirements for the CEO are listed; the excerpt focuses on disclosure of remuneration.

**Cited.** f03ab4a4ef9d7b37:4.3, 3a02ac314f68629e:3.2.3, b75f7fa613e6320e:3.1.3, bbfd16576f29b9c1:3.7.3
**Gold.** f03ab4a4ef9d7b37:4.3

> **Criteria for the Registration of an Insurance Broker [IA/II-G04] · f03ab4a4ef9d7b37:4.3**
>
> The  Chief  Executive  Officer  ['CEO']  and  Executive  Directors  ['EDs'] should have at least 5 years of relevant working experience. They should also have satisfactory academic and/or professional qualifications.  In addition, the CEO should have at least 3 years of managerial experience in the relevant field.
> Track Record

> **Guidelines on Licensing for Digital Token Service Providers · 3a02ac314f68629e:3.2.3**
>
> Competency of Key Individuals -  The  applicant  must  ensure that  its soleproprietor, partners, managers or executive directors and CEO have sufficient experience  in  operating  a  business  in  the  digital  token  services  industry, including having  sufficient understanding  of  the regulatory framework for DTSPs in Singapore.
> Where the  individual  will  be  managing  a  sizeable  team,  the  sole-proprietor, partners,  managers  or  executive  directors  and  CEO  should  also  have  the relevant experience, competencies, and influence, to allow them to exercise effective oversight and control over the business activities and staff.
> The  applicant should also consider the educational qualifications and professional certification of its key individuals.

> **Guidelines on Licensing for Payment Service Providers [PS-G01] (w.e.f 8 October 2025) · b75f7fa613e6320e:3.1.3**
>
> Competency of Key Individuals -  The applicant must ensure that its soleproprietor, partners, or executive directors and CEO have sufficient experience in operating a business in the payment services industry or related areas in the financial  services  industry,  including  having  sufficient  understanding  of  the regulatory framework for payment service providers in Singapore.
> Where the  individual  will  be  managing  a  sizeable  team,  the  sole-proprietor, partners,  or  executive  directors  and  CEO  should  also  have  the  relevant experience, competencies, and influence, to allow them to exercise effective oversight and control over the business activities and staff.
> The applicant should also consider the educational qualifications and professional certification of its key individuals.

> **Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05] · bbfd16576f29b9c1:3.7.3**
>
> Private equity and venture capital funds - Relevant experience may include experience  in  industry  segments  that  are  within  the  fund's  investment mandate.
> 3.8 MAS  does  not  consider  e xperience  in  investing  one's own  moneys  or  moneys belonging to family members, as being relevant experience in the context of an FMC that is seeking  to  manage  monies  for  third  parties. Where  an  individual's  past  experience  in investment management was gained at unregulated entities, the FMC must be prepared to substantiate the individual's experience. In addition, the period of relevant experience will be considered in assessing the competency of key individuals. For example, an individual with multiple short stints or with experience gained more than 10 years ago, may not be considered to possess the relevant experience required.
> 3.9 External Involvements of Key Individuals - CEOs and Executive Directors are expected to focus on the management of the FMC's business and may be required to divest outside business interests, if they are unable to adequately mitigate the conflicts of interest (whether actual or perceived), or reputational risks posed to the FMC.
> 3.10 Appointme

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 10. t-015 · single_agent  · **contested**

**Question.** For a bank dealing with an investment vehicle where the managers are financial institutions incorporated outside Singapore, under what specific conditions can it avoid performing CDD on the underlying investors?

**Answer.** Based on **Notice 626** (doc_id: `1b9b9f6db2876069`, section_path: `6.16`), a bank dealing with an investment vehicle where the managers are financial institutions incorporated outside Singapore can avoid performing CDD on the underlying investors under the following specific conditions:

## Conditions for Exemption from CDD on Underlying Investors

A bank is **not required to inquire** about beneficial owners of an investment vehicle if:

1. **The managers are financial institutions set out in Appendix 1**, OR
2. **The managers are incorporated or established outside Singapore but are subject to and supervised for compliance with AML/CFT requirements consistent with standards set by the FATF** (Financial Action Task Force)

## Important Caveat

This exemption applies **unless**:
- The bank has doubts about the veracity of the CDD information, OR
- The bank suspects that the customer, business relations with, or transaction for the customer may be connected with money laundering or terrorism financing.

In such cases, the bank must still perform CDD on the underlying investors regardless of the managers' status.

**Cited.** 1b9b9f6db2876069:6.16
**Gold.** 1b9b9f6db2876069:6.16, a0a676334344e6eb:2

> **Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · 1b9b9f6db2876069:6.16**
>
> A bank shall not be required to inquire if there exists any beneficial owner in relation to a customer that is -
> (a) an entity listed and traded on the Singapore Exchange;
> (b) an entity listed on a stock exchange outside of Singapore that is subject to -
> (i) regulatory disclosure requirements; and
> (ii) requirements relating to adequate transparency in respect of its beneficial owners (imposed through stock exchange rules, law or other enforceable means);
> (c) a financial institution set out in Appendix 1;
> (d) a financial institution incorporated or established outside Singapore that is subject to  and  supervised  for  compliance  with  AML/CFT  requirements  consistent  with standards set by the FATF; or
> (e) an investment vehicle where the managers are financial institutions 6  -
> (i) set out in Appendix 1; or
> (ii) incorporated  or  established  outside  Singapore  but  are  subject  to  and supervised for  compliance with AML/CFT requirements consistent with standards set by the FATF,
> unless the bank has doubts about the veracity of the CDD information, or suspects that the customer, business relations with, or transaction for the customer, may be connected with money laundering or

_mechanical:_ `{"success": false, "retrieved_gold": false, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 11. t-017 · single_agent  · **contested**

**Question.** For a Digital Payment Token Service Provider conducting its first non-face-to-face business contact with a customer, what specific external assessment must be appointed to evaluate the effectiveness of policies regarding impersonation risks?

**Answer.** For a Digital Payment Token Service Provider conducting its first non-face-to-face business contact with a customer, the MAS Notice FSM-N27 requires that the provider must, at its own expense, appoint an **external auditor or an independent qualified consultant** to assess the effectiveness of the policies and procedures mentioned in paragraph 6.39, including the effectiveness of technology solutions used to manage impersonation risks.

This requirement is specified in:
- **doc_id**: `b9a0d91d0de33dc4`
- **section_path**: `6.42`
- **Title**: MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism

The full text states: "Where a digital token service provider conducts its first non-face-to-face business contact, the digital token service provider must, at the digital token service provider's own expense, appoint an external auditor or an independent qualified consultant to assess the effectiveness of the policies and procedures mentioned in paragraph 6.39, including the effectiveness of technology solutions used to manage impersonation risks."

**Cited.** b9a0d91d0de33dc4:6.42
**Gold.** 5283d58b005b2342:6.37, 8164e80aa11d65e8:6

> **MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · b9a0d91d0de33dc4:6.42**
>
> Where  a  digital  token  service  provider  conducts  its  first  non-face-to-face  business contact, the digital token service provider must , at the digital token service provider's own expense, appoint an external auditor or an independent qualified consultant to assess the effectiveness of the policies and procedures mentioned in paragraph 6.39, including the effectiveness of technology solutions used to manage impersonation risks.

_mechanical:_ `{"success": false, "retrieved_gold": false, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 12. t-001 · single_agent

**Question.** What specific Probability of Default values should a Reporting Bank use when its calculated PD falls below the threshold for calculating KMort, KQRRE for transactors, and KQRRE for revolvers?

**Answer.** According to **Notice 637 Risk Based Capital Adequacy Requirements for Banks Incorporated in Singapore** (doc_id: `d60d84ece1ddaefe`), specifically section **7.4.88**:

> "For the purposes of calculating Kqrre pursuant to paragraph 7.4.85, the Reporting Bank must apply PD = 0.0005 where the PD is less than 0.0005 for a QRRE transactor and PD = 0.001 where the PD is less than 0.001 for a QRRE revolver."

Therefore:
- For **QRRE transactors**, if the calculated Probability of Default (PD) falls below **0.0005**, the Reporting Bank must use **PD = 0.0005**.
- For **QRRE revolvers**, if the calculated PD falls below **0.001**, the Reporting Bank must use **PD = 0.001**.

This same document also states that for calculating **Kmort** and **Koret**, a Reporting Bank must apply **PD = 0.0005** where the PD is less than 0.0005.

**Cited.** d60d84ece1ddaefe:7.4.88
**Gold.** d60d84ece1ddaefe:7.4.88

> **Notice 637 Risk Based Capital Adequacy Requirements for Banks Incorporated in Singapore · d60d84ece1ddaefe:7.4.88**
>
> For the purposes of calculating Kmort pursuant to paragraphs 7.4.82 to 7.4.84, and Koret pursuant to paragraph 7.4.86, a Reporting Bank must apply PD = 0.0005 where the PD is less than 0.0005. For the purposes of calculating Kqrre pursuant to paragraph 7.4.85, the Reporting Bank must apply PD = 0.0005 where the PD is less than 0.0005 for a QRRE transactor and PD = 0.001 where the PD is less than 0.001 for a QRRE revolver.
> Loss Given Default, LGD

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 13. t-002 · single_agent

**Question.** How often should an FMC monitor its managed assets to ensure it stays within specific limits?

**Answer.** Based on the **Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05]** (doc_id: `bbfd16576f29b9c1`), section **2.4**:

> "An FMC subject to specific limits on managed assets should **periodically monitor** the size of the assets being managed, for the purpose of ensuring that it is adhering to such limits."

The guidelines do not specify an exact frequency (e.g., daily, weekly, monthly), but rather require **periodic monitoring**. The FMC should also consider potential changes in asset size arising from:
- Prospecting of new investors
- Investment mandates

This means the monitoring frequency should be appropriate to the circumstances and should be sufficient to detect when managed assets might exceed the specific limits imposed on the FMC.

**Cited.** (nothing)
**Gold.** bbfd16576f29b9c1:2.3.3

_mechanical:_ `{"success": false, "retrieved_gold": true, "cited_resolvable": false, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 14. t-003 · plan_and_execute

**Question.** What data sources should an insurer use to validate the reasonableness of assumptions for base rates?

**Answer.** An insurer should use its own historical experience and that of the industry where relevant. These may be supplemented by other internal and external data (such as mortality or morbidity rates from reinsurers, or industry motor insurance statistics), and could include trends observed in claims costs and expenses. This approach is supported by Guidelines on Risk Management Practices for Insurance Business - Core Activities, clause 3.3.4.1.

**Cited.** a635e0bf93b047fa:3.3.4.1
**Gold.** a635e0bf93b047fa:3.3.4.1

> **Guidelines on ​Risk Management Practices for Insurance Business - Core Activities · a635e0bf93b047fa:3.3.4.1**
>
> An insurer should collect adequate data to validate the reasonableness of the underlying assumptions used for deriving the base rate of the product. The base rate (also known as the technical rate) should represent the amount required to meet the  value  of  anticipated  benefits,  expenses,  and  margins  for  risks  and/or  profit, independent of the supply and demand in the insurance market and any competitive consideration. Data should primarily relate to the insurer's own historical experience and that of the industry where relevant. These may be supplemented by other internal and external data (such as mortality or morbidity rates from reinsurers, or industry motor insurance  statistics),  and  could  include  trends  observed  in  claims  costs  and expenses.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 15. t-003 · single_agent

**Question.** What data sources should an insurer use to validate the reasonableness of assumptions for base rates?

**Answer.** Based on the **Guidelines on Risk Management Practices for Insurance Business - Core Activities** (doc_id: `a635e0bf93b047fa`, section 3.3.4.1), an insurer should use the following data sources to validate the reasonableness of assumptions for base rates:

## Primary Data Sources:
1. **Insurer's own historical experience** - The primary source of data should be the insurer's own historical claims and expense data.

2. **Industry experience** - Where relevant, data from the industry as a whole should also be used.

## Supplementary Data Sources:
3. **Other internal data** - Additional internal sources that may support validation.

4. **External data**, including:
   - Mortality or morbidity rates from reinsurers
   - Industry motor insurance statistics
   - Trends observed in claims costs and expenses

The guidelines state that these data sources should be collected to validate the reasonableness of underlying assumptions used for deriving the base rate, which represents the amount required to meet anticipated benefits, expenses, and margins for risks.

**Cited.** a635e0bf93b047fa:3.3.4.1
**Gold.** a635e0bf93b047fa:3.3.4.1

> **Guidelines on ​Risk Management Practices for Insurance Business - Core Activities · a635e0bf93b047fa:3.3.4.1**
>
> An insurer should collect adequate data to validate the reasonableness of the underlying assumptions used for deriving the base rate of the product. The base rate (also known as the technical rate) should represent the amount required to meet the  value  of  anticipated  benefits,  expenses,  and  margins  for  risks  and/or  profit, independent of the supply and demand in the insurance market and any competitive consideration. Data should primarily relate to the insurer's own historical experience and that of the industry where relevant. These may be supplemented by other internal and external data (such as mortality or morbidity rates from reinsurers, or industry motor insurance  statistics),  and  could  include  trends  observed  in  claims  costs  and expenses.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 16. t-003 · supervisor

**Question.** What data sources should an insurer use to validate the reasonableness of assumptions for base rates?

**Answer.** An insurer should use its own historical experience and that of the industry where relevant. These may be supplemented by other internal and external data (such as mortality or morbidity rates from reinsurers, or industry motor insurance statistics), and could include trends observed in claims costs and expenses. This approach is supported by Guidelines on Risk Management Practices for Insurance Business - Core Activities, clause 3.3.4.1.

**Cited.** a635e0bf93b047fa:3.3.4.1
**Gold.** a635e0bf93b047fa:3.3.4.1

> **Guidelines on ​Risk Management Practices for Insurance Business - Core Activities · a635e0bf93b047fa:3.3.4.1**
>
> An insurer should collect adequate data to validate the reasonableness of the underlying assumptions used for deriving the base rate of the product. The base rate (also known as the technical rate) should represent the amount required to meet the  value  of  anticipated  benefits,  expenses,  and  margins  for  risks  and/or  profit, independent of the supply and demand in the insurance market and any competitive consideration. Data should primarily relate to the insurer's own historical experience and that of the industry where relevant. These may be supplemented by other internal and external data (such as mortality or morbidity rates from reinsurers, or industry motor insurance  statistics),  and  could  include  trends  observed  in  claims  costs  and expenses.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 17. t-006 · single_agent

**Question.** What information regarding a customer's business relationship must a Commercial Money Institution obtain during the application process?

**Answer.** Based on my search results, I found relevant information about what a Commercial Money Institution (CMI) must obtain during the application process. The key requirement is:

**From Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism:**

According to **section 6.18** (doc_id: `2b1bc1dfa4766264`):

> "A CMI shall, when processing the application to establish business relations, understand and as appropriate, obtain from the customer information as to the purpose and intended nature of business relations."

This means that during the application process, a Commercial Money Institution must:

1. **Understand** the customer's business relationship
2. **Obtain from the customer** information regarding:
   - The **purpose** of the business relationship
   - The **intended nature** of the business relationship

This requirement applies when the CMI is processing an application to establish business relations with a customer.

Additionally, under **section 6.3** (doc_id: `2b1bc1dfa4766264`), CMIs must perform the measures required by paragraphs 6, 7, and 8 when they establish business relations with any customer, which includes the Customer Due Diligence (CDD) requirements outlined in those sections.

**Cited.** 2b1bc1dfa4766264:6.18, 2b1bc1dfa4766264:6.3
**Gold.** 2b1bc1dfa4766264:6.18

> **Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · 2b1bc1dfa4766264:6.18**
>
> A CMI shall, when processing the application to establish business relations, understand and as appropriate, obtain from the customer information as to the purpose and intended nature of business relations.
> (VI) Ongoing Monitoring

> **Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · 2b1bc1dfa4766264:6.3**
>
> A CMI shall perform the measures as required by paragraphs 6, 7 and 8 when -
> (a) the CMI establishes business relations with any customer;
> (b) the CMI undertakes any transaction of a value exceeding S$20,000, other than any digital CMP token transaction referred to in paragraph 6.3(c), for any customer who has not otherwise established business relations with the CMI;
> 4  Please note in particular section 57 of the CDSA on tipping-off.
> (c) the CMI undertakes any digital CMP token transactions for any customer who has not otherwise established business relations with the CMI;
> (d) the  CMI  effects  or  receives  any  digital  CMP  tokens  by  value  transfer,  for  any customer who has not otherwise established business relations with the CMI;
> (e) there is a suspicion of money laundering or terrorism financing, notwithstanding that  the  CMI  would  not  otherwise  be  required  by  this  Notice  to  perform  the measures as required by paragraphs 6, 7 and 8; or
> (f) the CMI has doubts about the veracity or adequacy of any information previously obtained.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 18. t-007 · single_agent

**Question.** What are the experience and qualification requirements for a CEO or an Executive Director?

**Answer.** Based on the search results, here are the experience and qualification requirements for a CEO or Executive Director:

**From Guidelines on Criteria for the Registration of an Insurance Broker [IA/II-G04] (effective 2021-10-08):**

According to section 4.3 of this document:
- **Both CEO and Executive Directors** should have:
  - At least **5 years of relevant working experience**
  - Satisfactory academic and/or professional qualifications

- **CEO specifically** should have in addition:
  - At least **3 years of managerial experience** in the relevant field

This is from doc_id `f03ab4a4ef9d7b37`, section_path `4.3`.

Note that other documents (like those for Digital Token Service Providers, Payment Service Providers, and REIT managers) have different requirements specific to their respective sectors, but the Insurance Broker guidelines provide clear, specific requirements for both roles.

**Cited.** f03ab4a4ef9d7b37:4.3
**Gold.** f03ab4a4ef9d7b37:4.3

> **Criteria for the Registration of an Insurance Broker [IA/II-G04] · f03ab4a4ef9d7b37:4.3**
>
> The  Chief  Executive  Officer  ['CEO']  and  Executive  Directors  ['EDs'] should have at least 5 years of relevant working experience. They should also have satisfactory academic and/or professional qualifications.  In addition, the CEO should have at least 3 years of managerial experience in the relevant field.
> Track Record

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 19. t-008 · plan_and_execute

**Question.** What record-keeping obligations apply to a licensee providing digital token services other than those mentioned in paragraph (j) of the FSM Act definition?

**Answer.** A licensee (other than a licensee that provides the service mentioned in paragraph (j) of the definition of 'digital token service' in paragraph 1 of Part 1 of the First Schedule to the FSM Act) must keep a record in the English language containing all the information set out in Annex A1, of all the licensee's transactions in respect of the digital token service the licensee is in the business of providing (MAS Notice FSM-N32 Conduct, clause 5).

**Cited.** cf7022fe78fb1df9:5
**Gold.** cf7022fe78fb1df9:5

> **MAS Notice FSM-N32 Conduct · cf7022fe78fb1df9:5**
>
> A  licensee  (other  than  a  licensee  that  provides  the  service  mentioned  in  paragraph  (j)  of  the definition of 'digital token service' in paragraph 1 of Part 1 of the First Schedule to the FSM Act) must keep a record in the English language containing all the information set out in Annex A1, of all the licensee's transactions in respect of the digital token service the licensee is in the business of providing.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---

## 20. t-008 · supervisor

**Question.** What record-keeping obligations apply to a licensee providing digital token services other than those mentioned in paragraph (j) of the FSM Act definition?

**Answer.** A licensee (other than a licensee that provides the service mentioned in paragraph (j) of the definition of 'digital token service' in paragraph 1 of Part 1 of the First Schedule to the FSM Act) must keep a record in the English language containing all the information set out in Annex A1, of all the licensee's transactions in respect of the digital token service the licensee is in the business of providing (MAS Notice FSM-N32 Conduct, clause 5).

**Cited.** cf7022fe78fb1df9:5
**Gold.** cf7022fe78fb1df9:5

> **MAS Notice FSM-N32 Conduct · cf7022fe78fb1df9:5**
>
> A  licensee  (other  than  a  licensee  that  provides  the  service  mentioned  in  paragraph  (j)  of  the definition of 'digital token service' in paragraph 1 of Part 1 of the First Schedule to the FSM Act) must keep a record in the English language containing all the information set out in Annex A1, of all the licensee's transactions in respect of the digital token service the licensee is in the business of providing.

_mechanical:_ `{"success": true, "retrieved_gold": true, "cited_resolvable": true, "abstained_correctly": true}`

```json
{"supported": null, "complete": null, "cited_correctly": null}
```

---
