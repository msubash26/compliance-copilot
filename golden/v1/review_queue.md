# Golden set v1 — human review queue

Ascending confidence: the items most likely to be wrong are first. Confidence is a
ranking device, not a calibrated probability — see ADR-017.

29 of 150 items carry at least one failed check.

## gs-0016 · factual_lookup · confidence 0.35

**Q.** What are the resource and independence requirements for the audit function of a Digital Payment Token Service provider?

**A.** A Digital Payment Token Service provider must maintain an audit function that is adequately resourced and independent. This function must be able to regularly assess how effective the provider's internal policies, procedures, controls, and regulatory compliance are.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 17.5

> A payment service provider shall maintain an audit function that is adequately resourced and independent, and that is able to regularly assess the effectiveness of the payment service provider 's internal policies, procedures and controls, and its compliance with regulatory requirements. Employee Hiring

---

## gs-0019 · factual_lookup · confidence 0.35

**Q.** How should an institution determine which outsourcing arrangements are considered material?

**A.** An institution must assess the materiality of an arrangement by considering factors such as the importance of the business activity, potential impacts on earnings and reputation, effects on customers and counterparties, costs involved, aggregate exposure to a single provider, and the ability to maintain internal controls.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — ​Guidelines on Outsourcing [Cancelled] · clause 6.8

> Institutions are ultimately responsible and accountable for maintaining oversight of CS and managing the attendant risks of adopting CS, as in any other form of outsourcing arrangements. A risk-based approach should be taken by institutions to ensure that the level of oversight and controls are commensurate with the materiality of the risks posed by the CS. EXAMPLES OF OUTSOURCING ARRANGEMENTS 1 The following are examples of some services that, when performed by a third party, would be regarded as outsourcing arrangements for the purposes of these Guidelines although they are not exhaustive: (a) application processing (e.g., loan origination, credit cards); (b) white-labelling arrangements such as for trading and hedging facilities; (c) middle and back office operations (e.g., electronic funds transfer, payroll processing, custody operations, quality control, purchasing, maintaining the

---

## gs-0054 · multi_hop · confidence 0.35

**Q.** When does a Digital Token Service Provider acting on a joint account need to perform customer due diligence on every holder, and what specific information must it send to the beneficiary institution regarding those holders?

**A.** The provider must treat all joint account holders as individual customers for due diligence purposes and provide complete details of each holder to the beneficiary institution.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Guidelines to MAS Notice FSM-N27 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Token Service Providers · clause 14

> 14-1 In relation to paragraph 14.1 of the Notice, value transfers include all forms of electronic transmission including, but not limited to, email, facsimile, short message service or other means of secure electronic transmission for payment instructions. 14-2 A digital token service provider may use any technology or software solution to transmit the necessary information in the message or payment instruction that accompanies or relates to the value transfer, as long as it enables the ordering institution and the beneficiary institution to comply with the requirements under paragraph 14 of the Notice. 14-3 A digital token service provider should not omit, delete or alter information in payment messages, for the purpose of avoiding detection of that information by another FI in the payment process. 14-4 A digital token service provider should monitor payment messages to and from higher

**Gold span** — MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.53

> In the case of a joint account, a digital token service provider must perform CDD measures on all of the joint account holders as if each of them is an individual customer of the digital token service provider. Existing Customers

---

## gs-0055 · multi_hop · confidence 0.35

**Q.** For a specified payment services provider, what specific enhanced due diligence actions are mandated for customers from higher-risk sectors like shell companies or cash-intensive businesses, and under what exception related to politically exposed persons might these requirements not apply?

**A.** A specified payment service provider must perform enhanced customer due diligence measures for high-risk categories such as shell companies and cash-intensive businesses, unless the relationship involves a domestic, international organization, or former politically exposed person who presents a lower risk profile.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Guidelines to Notice PSN01 on Prevention of Money Laundering and Countering the Financing of Terrorism - Specified Payment Services · clause 9

> 9-1 Where the ML/TF risks are identified to be higher, a payment service provider shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 9-2 Examples of potentially higher risk categories under paragraph 9.7 of the Notice include - (a) Customer risk (i) customers from higher risk businesses/ activities/ sectors identified in Singapore's NRA, guidance from the Authority, as well as other higher risk businesses/ activities/ sectors identified by the payment service provider; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relations with a customer or transaction undertaken without an account being opened is conducted under unusual circumstanc

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 9.5

> A payment service provider may adopt a risk-based approach in determining whether to perform enhanced CDD measures or the extent of enhanced CDD measures to be performed for ⎯ (a) domestic politically exposed persons, their family members and close associates; (b) international organisation politically exposed persons, their family members and close associates; or (c) politically exposed persons who have stepped down from their prominent public functions, taking into consideration the level of influence such persons may continue to exercise after stepping down from their prominent public functions, their family members and close associates, except in cases where their business relations with the payment service provider or transactions (except for specified money-changing transactions) without an account being opened by the payment service provider present a higher risk for money launder

---

## gs-0056 · multi_hop · confidence 0.35

**Q.** What specific enhanced CDD measures must a Credit Card or Charge Card licensee implement for customers identified as higher risk by either the Authority or other relevant authorities in Singapore?

**A.** A licensee shall perform appropriate enhanced customer due diligence measures for business relations with, or transactions undertaken for, any customer who presents a higher risk for money laundering or terrorism financing and is notified to the licensee by the Authority or other relevant authorities in Singapore.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Guidelines to Notice 626A on Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, a licensee shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.7 of the Notice include- (a) Customer risk (i) customers from higher risk businesses / activities / sectors identified in Singapore's NRA, as well as other higher risk businesses / activities / sectors identified by the licensee; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relation is conducted under unusual circumstances (e.g. significant unexplained geographic distance between the licensee and the customer); (v) companies that have nominee sharehol

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 8.7

> A licensee shall perform the appropriate enhanced CDD measures in paragraph 8.3 for business relations with, or transactions undertaken in the course of business relations for, any customer ⎯ (a) who the licensee determines under paragraph 8.5; or (b) the Authority or other relevant authorities in Singapore notify to the licensee, as presenting a higher risk for money laundering or terrorism financing.

---

## gs-0060 · multi_hop · confidence 0.35

**Q.** If a digital token service provider relies on an independent third party for customer due diligence, what specific limitation applies to that provider regarding ongoing transaction monitoring?

**A.** The digital token service provider is prohibited from relying on the third party to carry out ongoing monitoring or review of transactions without an account being opened.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Guidelines to MAS Notice FSM-N27 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Token Service Providers · clause 11

> 11-1 Paragraph 11 does not apply to outsourcing. Third party reliance under paragraph 11 of the Notice is different from an outsourcing arrangement or agreement. 11-2 In a third party reliance scenario, the third party will typically have an existing relationship with the customer that is independent of the relationship to be formed by the customer with the relying digital token service provider. The third party will therefore perform the CDD measures on the customer according to its own AML/CFT policies, procedures and controls. 11-3 In contrast to a third party reliance scenario, the outsourced service provider performs the CDD measures (e.g. performs centralised transaction monitoring functions) on behalf of the digital token service provider, in accordance with the digital token service provider's AML/CFT policies, procedures and standards, and is subject to the digital token service

**Gold span** — MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · clause 11

> Insurance brokers registered under the Insurance Act 1966 which, by virtue of the registration, are exempted under section 20(1)(c) of the Financial Advisers Act 2001 except those which only provide advice by issuing or promulgating research analyses or research reports, whether in electronic, print or other form, concerning an investment product.

---

## gs-0071 · multi_hop · confidence 0.35

**Q.** If a borrower contributes to another party's monthly repayments but that other party was unable to pay them at the time of application, does this contributor qualify as a borrower under the rules?

**A.** Yes, a person who contributes towards another party's monthly repayments is considered a borrower if the original applicant was assessed as unable to pay those instalments when applying for the credit facility.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice 115 Residential Property Loans · clause 30

> In this Notice, (a) 'Adjusted Purchase Price' means the purchase price after the deduction of - (i) the amount of any discount, rebate, or any other benefit (including the payment of legal or stamp fees for the purchase) offered by the vendor or any other party, whether directly or indirectly, arising from or resulting in the purchase of a Residential Property or in obtaining any credit facility for the purchase of a Residential Property, and which has the effect of reducing the true purchase price; and (ii) any interest in respect of any credit facility relating to the purchase which is paid or payable by the vendor, its agent, nominee or any other person by arrangement with the vendor, irrespective of whether payment is made to the direct insurer or as a benefit to the Borrower, or in the case where the Borrower is a vehicle set up for the purchase of Residential Property, the vehicle

**Gold span** — Notice 128 Computation of Total Debt Servicing Ratio for Property Loans · clause 2

> In this Notice, unless the context otherwise requires - (a) 'Borrower' means: (i) any natural person applying for a credit facility; (ii) any sole proprietorship applying for a credit facility, which is formed or established by a natural person, in or outside Singapore; or (iii) any vehicle set up for the purchase of Property, applying for a credit facility; [MAS Notice 128 (Amendment) 2013] [MAS Notice 128 (Amendment) 2017] (b) 'Bridging Loan' means a credit facility granted for the purchase of Residential Property by the Borrower, pending the receipt of proceeds from the sale of another Residential Property owned or co-owned by the Borrower, under which any balance outstanding must be repaid within six months; [MAS Notice 128 (Amendment) 2025] (c) 'business trust' has the same meaning as in section 2 of the Business Trusts Act 2004; [MAS Notice 128 (Amendment) 2025] (d) 'collective inv

---

## gs-0075 · multi_hop · confidence 0.35

**Q.** If a reporting bank chooses to use a more conservative peak exposure measure instead of effective EPE for estimating its exposure amount, how must this choice affect its treatment of collateral credit risk mitigation and what specific approval is required?

**A.** The bank must not recognize the effects of credit risk mitigation on that exposure, and it requires prior approval from the Authority to use such a conservative measure.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice 656 Exposures to Single Counterparty Groups for Banks Incorporated in Singapore · clause 2.8

> A Reporting Bank must not recognise the following: (a) other forms of collateral that are only eligible under the IRBA as set out in paragraph 2.11 of Annex 7H to Part VII of MAS Notice 637 to reduce exposure values; (b) the effects of CRM of any collateral for an exposure that has a maturity mismatch if the Reporting Bank has applied the FC(SA) under MAS Notice 637; (c) the effects of CRM if the Reporting Bank has not recognised this effect in the computation of credit RWA for the exposure in MAS Notice 637. [MAS Notice 656 (Amendment) 2024]

**Gold span** — Notice 637 Risk Based Capital Adequacy Requirements for Banks Incorporated in Singapore · clause 2.11

> Despite paragraphs 2.9 and 2.10 of this Annex, a Reporting Bank may use a measure that is more conservative than effective EPE to estimate E or EAD, whichever is applicable, for each counterparty, subject to the approval of the Authority. These measures include the use of peak exposure, the use of an EPE model as set out in Section 4 of this Annex or the use of VaR models as set out in Annex 7F. Section 3: Effective EPE

---

## gs-0076 · comparative · confidence 0.35

**Q.** How does the information sharing requirement for money laundering risk management apply to Capital Markets Intermediaries compared to the Depository and Financial Institutions Dealing In Precious Stones And Precious Metals?

**A.** Capital Markets Intermediaries and Financial Institutions Dealing In Precious Stones And Precious Metals must both share customer, account, and transaction information with their group-level functions when necessary for risk management, whereas the Depository is required to focus its efforts on ensuring regular and appropriate training for employees and officers regarding laws, suspicious transfer detection, and internal controls.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 14.7

> Such policies and procedures shall include the provision, to the CMI's group -level compliance, audit, and AML/CFT functions, of customer, account, and transaction information from its branches and subsidiaries within the financial group, when necessary for money laundering and terrorism financing risk management purposes. 14.7A For the purposes of paragraph 14.7, the information to be shared with the CMI's financial group shall include any information and analysis of transactions or activities that appear unusual. 13

**Gold span** — Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 14.7

> The Depository shall take all appropriate steps to ensure that its employees and officers are regularly and appropriately trained on - (a) AML/CFT laws and regulations, and in particular, CDD measures, and detecting and reporting of suspicious transfers; (b) prevailing techniques, methods and trends in money laundering and terrorism financing; and (c) the Depository's internal AML/CFT policies, procedures and controls, and the roles and responsibilities of employees, officers and representatives in combating money laundering and terrorism financing. Appendix 1

**Gold span** — Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · clause 14.7

> Such policies and procedures shall include the provision, to the financial institution's group-level compliance, audit, and AML/CFT functions, of customer, account, and transaction information from its branches and subsidiaries within the financial group, when necessary for money laundering and terrorism financing risk management purposes. 14.7A For the purposes of paragraph 14.7, the information to be shared within the financial institution's financial group shall include any information and analysis of transactions or activities that appear unusual. 8

---

## gs-0084 · comparative · confidence 0.35

**Q.** How do the obligations regarding information sharing and group-level oversight differ between Digital Payment Token Services and Specified Payment Services?

**A.** Digital Payment Token Services must develop group policies to share customer and transaction information across their financial group for AML/CFT risk management, whereas Specified Payment Services are restricted from providing individuals with access to their personal data, details on how that data was used, or the right to correct errors.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 17.2

> Subject to paragraph 17.3 and for the purposes of complying with this Notice, a payment service provider shall not be required to provide an individual customer, an individual appointed to act on behalf of a customer, an individual connected party of a customer or an individual beneficial owner of a customer, with ⎯ (a) any access to personal data about the individual that is in the possession or under the control of the payment service provider; (b) any information about the ways in which the personal data of the individual under subparagraph (a) has been or may have been used or disclosed by the payment service provider; and (c) any right to correct an error or omission of the personal data about the individual that is in the possession or under the control of the payment service provider.

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 17.2

> The policies, procedures and controls shall meet all the requirements of this Notice. Group Policy 17.2A For the purposes of paragraphs 17.2A to 17.H, a reference to 'payment service provider' means a payment service provider incorporated in Singapore. 17.2B A payment service provider shall develop a group policy on AML/CFT to meet all the requirements of this Notice and extend this to all of its branches and subsidiaries in its financial group. 17.2C Where a payment service provider has a branch or subsidiary in a host country or jurisdiction - (a) in relation to which the FATF has called for countermeasures; or (b) known to have inadequate AML/CFT measures, as determined by the payment service provider for itself, or notified to payment service providers generally by the Authority or other foreign regulatory authorities, the payment service provider shall ensure that its group policy o

---

## gs-0087 · comparative · confidence 0.35

**Q.** How do the requirements for qualifying AML/CFT compliance officers and ensuring they have access to necessary information differ between Digital Payment Token Service providers and Credit Card or Charge Card Licensees?

**A.** The requirement is the same for both institution types, as each must ensure their AML/CFT compliance officer and any assistants are suitably qualified, have adequate resources, and possess timely access to all customer records and relevant information needed to perform their functions.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 17.4

> A payment service provider shall ensure that the AML/CFT compliance officer, as well as any other persons appointed to assist the AML/CFT compliance officer, is suitably qualified and, has adequate resources and timely access to all customer records and other relevant information which the AML/CFT compliance officer requires to discharge the AML/CFT compliance officer's functions. Audit

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 17.4

> A licensee shall ensure that the AML/CFT compliance officer, as well as any other persons appointed to assist the AML/CFT compliance officer, is suitably qualified, and has adequate resources and timely access to all customer records and other relevant information which the AML/CFT compliance officer requires to discharge the AML/CFT compliance officer's functions. Audit

---

## gs-0096 · comparative · confidence 0.35

**Q.** How does the record-keeping obligation for wire transfer information differ among Banks, Merchant Banks, and Finance Companies when technical limitations prevent data from accompanying a cross-border transfer?

**A.** The requirement is identical for all three institution types; in each case, the receiving intermediary must retain a full record of the transmitted information for at least five years.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 11.14

> Where technical limitations prevent the required wire transfer originator or wire transfer beneficiary information accompanying a cross-border wire transfer from remaining with a related domestic wire transfer, a record shall be kept, for at least five years, by the receiving intermediary institution of all the information received from the ordering institution or another intermediary institution.

**Gold span** — Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks · clause 11.14

> Where technical limitations prevent the required wire transfer originator or wire transfer beneficiary information accompanying a cross-border wire transfer from remaining with a related domestic wire transfer, a record shall be kept, for at least five years, by the receiving intermediary institution of all the information received from the ordering institution or another intermediary institution.

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 11.14

> Where technical limitations prevent the required wire transfer originator or wire transfer beneficiary information accompanying a cross-border wire transfer from remaining with a related domestic wire transfer, a record shall be kept, for at least five years, by the receiving intermediary institution of all the information received from the ordering institution or another intermediary institution.

---

## gs-0097 · comparative · confidence 0.35

**Q.** Do Banks, Merchant Banks, and Finance Companies all share the same obligation to use reasonable, straight-through processing measures to spot cross-border wire transfers missing originator or beneficiary details?

**A.** Yes, the requirement is identical for all three institution types: each must take reasonable measures consistent with straight-through processing to identify cross-border wire transfers lacking the required originator or beneficiary information.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 11.15

> An intermediary institution shall take reasonable measures, which are consistent with straight-through processing, to identify cross-border wire transfers that lack the required wire transfer originator or wire transfer beneficiary information.

**Gold span** — Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks · clause 11.15

> An intermediary institution shall take reasonable measures, which are consistent with straight-through processing, to identify cross-border wire transfers that lack the required wire transfer originator or wire transfer beneficiary information.

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 11.15

> An intermediary institution shall take reasonable measures, which are consistent with straight-through processing, to identify cross-border wire transfers that lack the required wire transfer originator or wire transfer beneficiary information.

---

## gs-0098 · comparative · confidence 0.35

**Q.** How does the rule for retaining records of value transfer information when technical limits cause data separation apply to Digital Payment Token Service providers versus Credit Card or Charge Card Licensees?

**A.** The requirement is identical for both institution types; in either case, the receiving intermediary must keep a record of all information received from the ordering institution or another intermediary for at least five years.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 13.18

> Where technical limitations prevent the required value transfer originator or value transfer beneficiary information accompanying a value transfer from remaining with a related value transfer, a record shall be kept, for at least five years, by the receiving intermediary institution of all the information received from the ordering institution or another intermediary institution.

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 13.18

> Where technical limitations prevent the required value transfer originator or value transfer beneficiary information accompanying a value transfer from remaining with a related value transfer, a record shall be kept, for at least five years, by the receiving intermediary institution of all the information received from the ordering institution or another intermediary institution.

---

## gs-0099 · comparative · confidence 0.35

**Q.** How do the requirements for Digital Payment Token Service providers compare to those for Credit Card or Charge Card Licensees regarding handling value transfers with missing originator or beneficiary details?

**A.** The requirements are identical for both institution types; each must take reasonable measures consistent with straight-through processing to identify such transfers.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 13.19

> An intermediary institution shall take reasonable measures, which are consistent with straight-through processing, to identify value transfers that lack the required value transfer originator or value transfer beneficiary information.

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 13.19

> An intermediary institution shall take reasonable measures, which are consistent with straight-through processing, to identify value transfers that lack the required value transfer originator or value transfer beneficiary information.

---

## gs-0100 · comparative · confidence 0.35

**Q.** Do the internal risk-based policies required for handling value transfers missing originator or beneficiary information differ between Digital Payment Token Service providers and Credit Card or Charge Card Licensees?

**A.** The requirement is identical for both institution types, as they must both implement appropriate internal risk-based policies, procedures, and controls to determine when to execute, reject, or suspend such transfers and define the necessary follow-up actions.

**Failed checks:** judge_disagrees_with_answer, judge_says_not_answerable_from_span

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 13.20

> An intermediary institution shall implement appropriate internal risk-based policies, procedures and controls for determining ⎯ (a) when to execute, reject, or suspend a value transfer lacking required value transfer originator or value transfer beneficiary information; and (b) the appropriate follow-up action.

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 13.20

> An intermediary institution shall implement appropriate internal risk-based policies, procedures and controls for determining ⎯ (a) when to execute, reject, or suspend a value transfer lacking required value transfer originator or value transfer beneficiary information; and (b) the appropriate follow-up action.

---

## gs-0118 · negative · confidence 0.4

**Q.** Under Notice 653 Net Stable Funding Ratio Disclosure, what specific disclosure formats or supplementary reporting templates are financial institutions required to submit today?

**A.** This question cannot be answered from the corpus of MAS notices and guidelines because MAS documents typically prescribe quantitative ratios and high-level qualitative principles rather than mandating specific visual disclosure formats or providing downloadable supplementary reporting templates.

**Failed checks:** negative_is_answerable

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0026 · factual_lookup · confidence 0.6

**Q.** What terms must be included in an outsourcing agreement entered into by an intragroup entity on behalf of the bank before obtaining relevant services?

**A.** If an intragroup entity enters into an outsourcing agreement on behalf of the bank, the bank must ensure that the required terms are included before obtaining or receiving the material ongoing outsourced service.

**Failed checks:** judge_says_not_answerable_from_span

**Gold span** — Notice 658 Management of Outsourced Relevant Services for Banks · clause 7.2

> Where an intragroup entity of the bank in Singapore has entered into an outsourcing agreement on behalf of the bank, the bank must ensure that the terms set out in paragraph 7.1 are included in the outsourcing agreement before obtaining or receiving the material ongoing outsourced relevant service.

---

## gs-0003 · factual_lookup · confidence 0.75

**Q.** When does a reporting bank have to classify an exposure as defaulted?

**A.** A bank must record a default if it believes the borrower will not pay its debts without further action, the debt is more than 90 days past due, specific indicators of unlikeliness to pay are present, or a related obligor has defaulted.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice 637 Risk Based Capital Adequacy Requirements for Banks Incorporated in Singapore · clause Section 1: Definition of Default/1.1

> A Reporting Bank must record a default on any exposure to a particular obligor if - (a) it considers that the obligor is unlikely to pay its credit obligations to the banking group in full, without recourse by the Reporting Bank or any of its banking group entities to actions including realising collateral; or (b) the obligor is past due more than 90 days on any credit obligation to the banking group. 1.2 For the purposes of paragraph 1.1 of this Annex, for an IRBA exposure, the Authority may permit an extension of days past due beyond 90 days for a foreign PSE obligor, of up to 180 days, if a Reporting Bank requests such permission and provides strong justification for the extension. 1.3 If the Reporting Bank considers that paragraph 1.1 of this Annex no longer applies to a previously defaulted exposure, the Reporting Bank must assign a new obligor and facility grade to the exposure usi

---

## gs-0015 · factual_lookup · confidence 0.75

**Q.** What specific provisions must a written agreement include when a registered insurer borrows securities from an accredited investor?

**A.** A prior written agreement must be entered into between the parties to record the borrowing terms and conditions, regardless of whether collateral is provided. This agreement must define the capacities of the parties, detail title transfers for securities and collateral worth at least 100% of the borrowed value, outline rights regarding dividends and corporate actions, specify fee calculations, require daily mark-to-market procedures, describe return procedures, allow for early termination with fees, address set-off rights, list default events, and state the governing law and jurisdiction.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice 113 Securities Borrowing and Lending Activities · clause 9

> For the purposes of paragraph 8, the written agreement shall - ( a ) state the capacities in which the parties are entering into the agreement (whether as principal or agent); ( b ) provide for the transfer of the title to and interest in the securities lent from the lender to the registered insurer, or the registered insurer to the borrower, as the case may be; ( c ) provide for the transfer of the title to and interest in the whole or part of the Collateral, provided or obtained by the registered insurer which is valued to be at least 100% of the market value of the securities (referred to in this regulation as minimum Collateral) which is borrowed by the registered insurer from the lender, or lent by the registered insurer to the borrower, as the case may be; ( d ) provide for the following rights throughout the period that the securities are borrowed or lent: (i) in the case where th

---

## gs-0032 · factual_lookup · confidence 0.75

**Q.** What specific factors should a depository consider when determining that a customer presents higher money laundering or terrorist financing risks?

**A.** A depository should apply enhanced due diligence measures when customers belong to high-risk sectors, have complex ownership structures, act as asset holding vehicles, operate under unusual circumstances, involve nominee arrangements, are cash-intensive, or exhibit characteristics of shell companies. Additionally, the institution must consider countries with high levels of corruption, organized crime, or inadequate anti-money laundering controls.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Guidelines to Notice SFA 03AA-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, the Depository shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.5 of the Notice include - (a) Customer risk (i) customers from higher risk businesses / activities / sectors identified in Singapore's NRA, as well as other higher risk businesses / activities / sectors identified by the Depository; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relationship is conducted under unusual circumstances (e.g. significant unexplained geographic distance between the Depository and the customer); (v) companies that have nom

---

## gs-0040 · factual_lookup · confidence 0.75

**Q.** How should an Approved Exchange or Recognised Market Operator conduct its enterprise-wide money laundering and terrorist financing risk assessment?

**A.** An Approved Exchange or Recognised Market Operator must perform a consolidated assessment covering all business units, product lines, and delivery channels to understand its overall vulnerability. Senior management must approve this assessment, which involves considering customer profiles, the jurisdictions involved, and the nature of services offered through both qualitative and quantitative analyses.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Guidelines to Notice SFA02-N05 on Prevention of Money Laundering and Countering the Financing of Terrorism - Approved Exchanges and Recognised Market Operators · clause 4

> Countries or Jurisdictions of its Customers 4-1 In relation to a customer who is a natural person, this refers to the nationality and place of domicile, business or work. For a customer who is a legal person or arrangement, this refers to both the country or jurisdiction of establishment, incorporation, or registration and, if different, the country or jurisdiction of operations as well. Other Relevant Authorities in Singapore 4-2 Examples include law enforcement authorities (e.g. Singapore Police Force, Commercial Affairs Department, Corrupt Practices Investigation Bureau) and other government authorities (e.g. Attorney General's Chambers, Ministry of Home Affairs, Ministry of Finance, Ministry of Law). Risk Assessment 4-3 In addition to assessing the ML/TF risks presented by an individual customer, an AE or RMO shall identify and assess ML/TF risks on an enterprise-wide level. 4 This s

---

## gs-0065 · multi_hop · confidence 0.75

**Q.** For a Capital Markets Intermediary that has determined low money laundering and terrorism financing risks for a customer and their beneficial owners, what simplified due diligence measures are permitted regarding the frequency of updating customer identification information and the extent of ongoing transaction monitoring?

**A.** The institution may reduce how often it updates customer identification details and lower the level of scrutiny on transactions, provided these reductions are based on reasonable monetary thresholds.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Guidelines to Notice SFA 04-N02 on Prevention of Money Laundering and Countering the Financing of Terrorism - Capital Markets Intermediaries · clause 7

> 7-1 Paragraph 7.1 of the Notice permits a CMI to adopt a risk-based approach in assessing the necessary measures to be performed, and to perform appropriate SCDD measures in cases where the CMI is satisfied, upon analysis of risks, that the ML/TF risks are low. 7-2 Where a CMI applies SCDD measures, it is still required to perform ongoing monitoring of business relations under the Notice. 7-3 Under SCDD, a CMI may adopt a risk-based approach in assessing whether any measures should be performed for connected parties of the customers. 7-4 Where a CMI is satisfied that the risks of money laundering and terrorism financing are low, a CMI may perform SCDD measures. Examples of possible SCDD measures include - (a) reducing the frequency of updates of customer identification information; (b) reducing the degree of ongoing monitoring and scrutiny of transactions, based on a reasonable monetary

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 7.1

> Subject to paragraph 7.4, a CMI may perform simplified CDD measures in relation to a customer, any natural person appointed to act on behalf of the customer and any beneficial owner of the customer (other than any beneficial owner that the CMI is exempted from making inquiries about under paragraph 6.16) if it is satisfied that the risks of money laundering and terrorism financing are low.

---

## gs-0079 · comparative · confidence 0.75

**Q.** How do the money laundering compliance obligations for Trust Companies differ from those applicable to Capital Markets Intermediaries and Depositories regarding internal controls, tipping-off provisions, and record-keeping?

**A.** Trust Companies must develop policies considering their specific risk profile, including adherence to Section 57 of the CDSA on tipping-off, whereas Capital Markets Intermediaries and Depositories are specifically required to establish a single reference point for referring suspicious transactions and maintaining records of those referrals.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 13.1

> A trust company shall develop and implement adequate internal policies, procedures and controls, taking into consideration its money laundering and terrorism financing risks and 9 Please note in particular section 57 of the CDSA on tipping-off. the size of its business, to help prevent money laundering and terrorism financing and communicate these to its employees.

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 13.1

> A CMI shall keep in mind the provisions in the CDSA 12 and in the TSOFA that provide for the reporting to the authorities of transactions suspected of being connected with money laundering or terrorism financing and implement appropriate internal policies, procedures and controls for meeting its obligations under the law, including the following: (a) establish a single reference point within the organisation to whom all employees, officers and representatives are instructed to promptly refer all transactions suspected of being connected with money laundering or terrorism financing, for possible referral to STRO via STRs; and (b) keep records of all transactions referred to STRO, together with all internal findings and analysis done in relation to them.

**Gold span** — Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 13.1

> The Depository shall keep in mind the provisions in the CDSA 6 and in the TSOFA that provide for the reporting to the authorities of transactions suspected of being connected with money laundering or terrorism financing and implement appropriate internal policies, procedures and controls for meeting its obligations under the law, including the following: (a) establish a single reference point within the organisation to whom all employees and officers are instructed to promptly refer all transfers undertaken in the course of business relations suspected of being connected with money laundering or terrorism financing, for possible referral to STRO via STRs; and (b) keep records of all transfers referred to STRO, together with all internal findings and analysis done in relation to them.

---

## gs-0086 · comparative · confidence 0.75

**Q.** How do the training obligations for anti-money laundering and counter-terrorist financing differ among Capital Markets Intermediaries, Financial Institutions Dealing In Precious Stones And Precious Metals, and Variable Capital Companies?

**A.** The core requirement is identical across all three institution types, mandating regular and appropriate training on AML/CFT laws, money laundering trends, and internal policies for employees and officers regardless of location. The only variation lies in the specific terminology used to refer to the entity itself, which shifts from 'CMI' to 'financial institution' and 'VCC', while the substantive scope of the obligation remains the same.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 14.14

> A CMI shall take all appropriate steps to ensure that its employees, officers and representatives (whether in Singapore or elsewhere) are regularly and appropriately trained on - (a) AML/CFT laws and regulations, and in particular, CDD measures, and detecting and reporting of suspicious transactions; (b) prevailing techniques, methods and trends in money laundering and terrorism financing; and (c) the CMI's internal AML/CFT policies, procedures and controls, and the roles and responsibilities of employees, officers and representatives in combating money laundering and terrorism financing.

**Gold span** — Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · clause 14.14

> A financial institution shall take all appropriate steps to ensure that its employees and officers (whether in Singapore or elsewhere) are regularly and appropriately trained on - (a) AML/CFT laws and regulations, and in particular, CDD measures, and detecting and reporting of suspicious transactions; (b) prevailing techniques, methods and trends in money laundering and terrorism financing; and (c) the financial institution's internal AML/CFT policies, procedures and controls, and the roles and responsibilities of employees and officers in combating money laundering and terrorism financing. Appendix 1

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 14.14

> A VCC shall take all appropriate steps to ensure that its employees and officers (whether in Singapore or elsewhere) are regularly and appropriately trained on ⎯ (a) AML/CFT laws and regulations, and in particular, CDD measures, and detecting and reporting of suspicious transactions; (b) prevailing techniques, methods and trends in money laundering and terrorism financing; and (c) the VCC's internal AML/CFT policies, procedures and controls, and the roles and responsibilities of employees and officers in combating money laundering and terrorism financing. [MAS Notice VCC-N01 (Amendment) 2022] Endnotes on History of Amendments

---

## gs-0093 · comparative · confidence 0.75

**Q.** For both Specified Payment Services and Variable Capital Companies (VCCs), does the requirement to scrutinize customer transactions based on their business profile differ, or are they identical?

**A.** The requirement is identical for both institution types; each must ensure that transactions conducted during the course of business relations are consistent with the entity's knowledge of the customer, its business and risk profile, and where appropriate, the source of funds.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 7.27

> A payment service provider shall, during the course of business relations with a customer, observe the conduct of the customer's account and scrutinise transactions undertaken throughout the course of business relations, to ensure that the transactions are consistent with the payment service provider 's knowledge of the customer, its business and risk profile and where appropriate, the source of funds.

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 7.27

> A VCC shall, during the course of business relations with a customer, scrutinise transactions undertaken throughout the course of business relations, to ensure that the transactions are consistent with the VCC's knowledge of the customer, its business and risk profile and where appropriate, the source of funds.

---

## gs-0095 · comparative · confidence 0.75

**Q.** How do the value transfer obligations for banks, merchant banks, and finance companies differ regarding internal risk-based policies for transfers lacking originator or beneficiary information?

**A.** The core obligation to implement internal risk-based policies, procedures, and controls for handling wire transfers missing required originator or beneficiary data is identical across banks, merchant banks, and finance companies. However, the specific definitions within those policies must be tailored to each entity type, as the regulations explicitly assign these duties to banks, merchant banks, and finance companies respectively while excluding non-self-transfers between institutions.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 11.16

> An intermediary institution shall implement appropriate internal risk-based policies, procedures and controls for determining - (a) when to execute, reject, or suspend a wire transfer lacking required wire transfer originator or wire transfer beneficiary information; and (b) the appropriate follow-up action. 11A VALUE TRANSFERS 11A.1 Paragraph 11A shall apply to a bank when: (a) it effects the sending of one or more digital tokens by value transfer; or (b) when it receives one or more digital tokens by value transfer on the account of the value transfer originator or the value transfer beneficiary, but shall not apply to a transfer and settlement between the bank and another financial institution where the bank and the other financial institution are acting on their own behalf as the value transfer originator and the value transfer beneficiary. 11A.2 For the purposes of paragraph 11A - '

**Gold span** — Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks · clause 11.16

> An intermediary institution shall implement appropriate internal risk-based policies, procedures and controls for determining - (a) when to execute, reject, or suspend a wire transfer lacking required wire transfer originator or wire transfer beneficiary information; and (b) the appropriate follow-up action. 11A VALUE TRANSFERS 11A.1 Paragraph 11A shall apply to a merchant bank when: (a) it effects the sending of one or more digital tokens by value transfer, or (b) when it receives one or more digital tokens by value transfer on the account of the value transfer originator or the value transfer beneficiary, but shall not apply to a transfer and settlement between the merchant bank and another financial institution where the merchant bank and the other financial institution are acting on their own behalf as the value transfer originator and the value transfer beneficiary. 11A.2 For the pu

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 11.16

> An intermediary institution shall implement appropriate internal risk-based policies, procedures and controls for determining - (a) when to execute, reject, or suspend a wire transfer lacking required wire transfer originator or wire transfer beneficiary information; and (b) the appropriate follow-up action. 11A VALUE TRANSFERS 11A.1 Paragraph 11A shall apply to a finance company when: (a) it effects the sending of one or more digital tokens by value transfer; or (b) it receives one or more digital tokens by value transfer on the account of the value transfer originator or the value transfer beneficiary, but shall not apply to a transfer and settlement between the finance company and another financial institution where the finance company and the other financial institution are acting on their own behalf as the value transfer originator and the value transfer beneficiary. 11A.2 For the p

---

## gs-0113 · temporal · confidence 0.75

**Q.** When did the requirement for separate records of each private equity or venture capital investment apply, and which instrument caused any changes to that rule?

**A.** The requirement for banks to keep separate records for internal monitoring applied under a specific instrument, but section 10.2 was later removed by MAS Notice 630 (Amendment) 2021.

**Failed checks:** judge_disagrees_with_answer

**Gold span** — Notice 630 Private Equity and Venture Capital Investments · clause 10

> 10.1 [Deleted by MAS Notice 630 (Amendment) 2021] 10.2 A bank in Singapore must ensure that each PE/VC investment is identifiable and that separate records for each PE/VC investment are kept for internal monitoring purposes. [MAS Notice 630 (Amendment) 2021]

---

## gs-0031 · factual_lookup · confidence 0.85

**Q.** What enhanced customer due diligence measures must a Financial Institution Dealing In Precious Stones And Precious Metals perform for a politically exposed person?

**A.** Such institutions must obtain senior management approval to establish or continue relationships, determine the source of wealth and funds, and conduct enhanced monitoring to detect unusual transactions.

**Failed checks:** answerable_without_corpus

**Gold span** — Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · clause 8.3

> A financial institution shall, in addition to performing CDD measures (specified in paragraph 6), perform at least the following enhanced CDD measures where a customer or any beneficial owner of the customer is determined by the financial institution to be a politically exposed person, or a family member or close associate of a politically exposed person under paragraph 8.2: (a) obtain approval from the financial institution's senior management to establish or continue an account relationship with the customer or undertake any relevant business transaction without an account opened for the customer; (b) establish, by appropriate and reasonable means, the source of wealth and source of funds of the customer and any beneficial owner of the customer; and (c) conduct, during the course of an account relationship with, or when undertaking transactions in the course of the account relationship

---

## gs-0001 · factual_lookup · confidence 1.0

**Q.** What specific Probability of Default values should a Reporting Bank use when its calculated PD falls below the threshold for calculating KMort, KQRRE for transactors, and KQRRE for revolvers?

**A.** For calculating KMort, the bank must apply a probability of default of 0.0005 if the actual value is lower. When calculating KQRRE, the bank applies 0.0005 for transactors and 0.001 for revolvers whenever their respective calculated probabilities are below those limits.

**Gold span** — Notice 637 Risk Based Capital Adequacy Requirements for Banks Incorporated in Singapore · clause 7.4.88

> For the purposes of calculating Kmort pursuant to paragraphs 7.4.82 to 7.4.84, and Koret pursuant to paragraph 7.4.86, a Reporting Bank must apply PD = 0.0005 where the PD is less than 0.0005. For the purposes of calculating Kqrre pursuant to paragraph 7.4.85, the Reporting Bank must apply PD = 0.0005 where the PD is less than 0.0005 for a QRRE transactor and PD = 0.001 where the PD is less than 0.001 for a QRRE revolver. Loss Given Default, LGD

---

## gs-0002 · factual_lookup · confidence 1.0

**Q.** How often should an FMC monitor its managed assets to ensure it stays within specific limits?

**A.** An FMC subject to specific limits on managed assets should periodically monitor the size of the assets being managed to ensure compliance with those limits.

**Gold span** — Guidelines on Licensing and Conduct of Business for Fund Management Companies [SFA 04-G05] · clause 2.3.3

> moneys and assets contracted to the FMC, but which have been subcontracted to another party and for which the other party is carrying out fund management, whether on a discretionary authority granted by the customer or otherwise. 2.4 Exceeding the Limit of Managed Assets - An FMC subject to specific limits on managed assets should periodically monitor the size of the assets being managed, for the purpose of ensuring that it is adhering to such limits. The FMC should, among other things, consider potential changes in the size of the assets being managed arising from prospecting of new investors or investment mandates.

---

## gs-0004 · factual_lookup · confidence 1.0

**Q.** What data sources should an insurer use to validate the reasonableness of assumptions for base rates?

**A.** An insurer must collect sufficient data based primarily on its own historical experience and relevant industry data to confirm that base rate assumptions are reasonable. Additional internal or external information, such as mortality statistics from reinsurers or observed trends in claims costs, may be used to supplement this primary data.

**Gold span** — Guidelines on ​Risk Management Practices for Insurance Business - Core Activities · clause 3.3.4.1

> An insurer should collect adequate data to validate the reasonableness of the underlying assumptions used for deriving the base rate of the product. The base rate (also known as the technical rate) should represent the amount required to meet the value of anticipated benefits, expenses, and margins for risks and/or profit, independent of the supply and demand in the insurance market and any competitive consideration. Data should primarily relate to the insurer's own historical experience and that of the industry where relevant. These may be supplemented by other internal and external data (such as mortality or morbidity rates from reinsurers, or industry motor insurance statistics), and could include trends observed in claims costs and expenses.

---

## gs-0005 · factual_lookup · confidence 1.0

**Q.** When does this notice become effective and which previous notice is replaced?

**A.** This notice takes effect on 20 July 2015, at which time MAS Notice 211 dated 22 June 2007 is cancelled.

**Gold span** — MAS Notice 211 - Minimum and Best Practice Training and Competency Standards for Direct General Insurers · clause 12

> This Notice shall take effect from 20 July 2015. MAS Notice 211 dated 22 June 2007 will be cancelled from 20 July 2015. Notes on History of Amendments MAS Notice 211 (Amendment) 2020 dated 16 April 2020 with effect from 20 April 2020. MAS Notice 211 (Amendment) 2021 dated 28 June 2021 with effect from 1 July 2021. MAS Notice 211 (Amendment No. 2) 2021 dated 28 October 2021 with effect from 1 November 2021.

---

## gs-0006 · factual_lookup · confidence 1.0

**Q.** Which specific information sources should be used to screen customers against?

**A.** Customers must be screened against relevant money laundering and terrorist financing information sources, including lists provided by Singaporean authorities, the First Schedule of the TSOFA, and the FSM Sanctions Regulations.

**Gold span** — Guidelines on Prevention of Money Laundering and Countering the Financing of Terrorism - Direct General Insurance Business, Reinsurance Business, and Direct Life Insurance Business (Accident & Health Policies) · clause 5.1

> Screening of customers 11 should be carried out against relevant ML/TF information sources, which include designated names of individuals and entities within: (a) the lists and information provided by the Authority or other relevant authorities in Singapore in relation to ML/TF risks; (b) the First Schedule of the TSOFA; and 10 There should minimally be some form of regularity with regard to such training. 11 For the purposes of these Guidelines, the definition of the term 'customers' will vary depending on the type of insurance business (e.g. direct insurance business, reinsurance business), and is elaborated on in paragraphs 5.2 and 5.3 of these Guidelines. (c) the FSM Sanctions Regulations.

---

## gs-0007 · factual_lookup · confidence 1.0

**Q.** What information regarding a customer's business relationship must a Commercial Money Institution obtain during the application process?

**A.** A Commercial Money Institution must understand and, when appropriate, receive details about the purpose and intended nature of the customer's business relationship while processing the application to establish that relationship.

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.18

> A CMI shall, when processing the application to establish business relations, understand and as appropriate, obtain from the customer information as to the purpose and intended nature of business relations. (VI) Ongoing Monitoring

---

## gs-0008 · factual_lookup · confidence 1.0

**Q.** What are the experience and qualification requirements for a CEO or an Executive Director?

**A.** Both the Chief Executive Officer and Executive Directors must possess at least five years of relevant work experience along with satisfactory academic or professional qualifications. Additionally, the CEO specifically requires a minimum of three years of managerial experience in their specific field.

**Gold span** — Criteria for the Registration of an Insurance Broker [IA/II-G04] · clause 4.3

> The Chief Executive Officer ['CEO'] and Executive Directors ['EDs'] should have at least 5 years of relevant working experience. They should also have satisfactory academic and/or professional qualifications. In addition, the CEO should have at least 3 years of managerial experience in the relevant field. Track Record

---

## gs-0009 · factual_lookup · confidence 1.0

**Q.** What record-keeping obligations apply to a licensee providing digital token services other than those mentioned in paragraph (j) of the FSM Act definition?

**A.** A licensee must maintain records in English containing all information specified in Annex A1 for every transaction related to the digital token service they provide.

**Gold span** — MAS Notice FSM-N32 Conduct · clause 5

> A licensee (other than a licensee that provides the service mentioned in paragraph (j) of the definition of 'digital token service' in paragraph 1 of Part 1 of the First Schedule to the FSM Act) must keep a record in the English language containing all the information set out in Annex A1, of all the licensee's transactions in respect of the digital token service the licensee is in the business of providing.

---

## gs-0010 · factual_lookup · confidence 1.0

**Q.** When can an entity choose to report short positions at the trading desk level instead of the legal entity level?

**A.** An entity may elect to report its short sell orders and positions at the trading desk level if it finds consolidating data across desks administratively difficult or unduly onerous. This option allows each desk to report all its short positions independently, without needing to monitor the total aggregated position at the legal entity level to determine reporting obligations.

**Gold span** — Guidelines on the Regulation of Short Selling [SFA 07A-G01] · clause 5.2

> To cater to different decision-making and operational models, MAS provides institutional participants the flexibility to determine the level (i.e. legal entity or trading desk) at which their orders and positions should be consolidated. While a reporting obligation is imposed only when the short position at the legal entity level is equivalent to or more than the short position threshold on position day , an entity may choose to report short positions at the trading desk level regardless. This may be administratively easier for the entity as the entity will then not have to monitor the aggregated position at the legal entity level for the purpose of determining whether or not it has to submit a report to MAS in respect of that position day . Example 7: Legal entity level A proprietary trading firm has one portfolio manager responsible for three trading desks. The portfolio manager is the

---

## gs-0011 · factual_lookup · confidence 1.0

**Q.** What are the requirements for notifying the Authority about completed compensation related to valuation errors?

**A.** When compensation is completed in accordance with the relevant guidelines, the insurer must notify the Authority by submitting a report on its official letterhead through electronic means. This report needs to include all the specific information outlined in the Valuation Error Report Template.

**Gold span** — Notice 307 Investment-Linked Policies · clause 82

> The insurer should notify the Authority when such compensation has been completed in compliance with paragraphs 79 to 81. VALUATION ERROR REPORT TEMPLATE The valuation error report should be made using the insurer's company letterhead and sent via electronic means. The report should contain the following information:

---

## gs-0012 · factual_lookup · confidence 1.0

**Q.** What training and review obligations does a bank have regarding its staff's ability to handle environmental risk?

**A.** A bank must provide adequate expertise to its staff through capacity building and training so they can assess, manage, and monitor environmental risks effectively. The bank should also regularly update these programs to address new issues in environmental risk management.

**Gold span** — Guidelines on Environmental Risk Management for Banks · clause 4.16

> The bank should equip its staff, including through capacity building and training, with adequate expertise to assess, manage and monitor environmental risk in a rigorous, timely and efficient manner. The bank should regularly review such capacity building programmes to incorporate emerging issues relating to environmental risk management.

---

## gs-0013 · factual_lookup · confidence 1.0

**Q.** What actions must a digital token service provider take regarding customer accounts and transactions during business relations?

**A.** A digital token service provider must observe the conduct of a customer's account and scrutinize all transactions throughout the course of business relations. This is to ensure that these transactions are consistent with the provider's knowledge of the customer, its business and risk profile, and if appropriate, the source of funds.

**Gold span** — MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.31

> A digital token service provider must, during the course of business relations with a customer, observe the conduct of the customer's account and scrutinise transactions undertaken throughout the course of business relations, to ensure that the transactions are consistent with the digital tok en service provider's knowledge of the customer, its business and risk profile and if appropriate, the source of funds.

---

## gs-0014 · factual_lookup · confidence 1.0

**Q.** If a collective investment scheme uses leverage or derivatives to generate returns, what additional sources of liquidity demands must an FMC consider in its management framework besides investor redemptions?

**A.** An FMC managing such a scheme must consider potential liquidity demands arising from margin or collateral calls from derivative counterparties as part of its overall liquidity risk management framework.

**Gold span** — Guidelines on Liquidity Risk Management Practices (Fund Management Companies) [SFA 04-G08] · clause 1.5

> Investor redemptions are not the only source of potential liquidity demands for a CIS. Liquidity demands may also arise from margin or collateral calls from derivative counterparties where leverage and/or derivatives are used as part of the investment strategy of the CIS. An FMC managing such CIS should consider these potential sources of liquidity risks as part of its liquidity risk management framework.

---

## gs-0017 · factual_lookup · confidence 1.0

**Q.** What are the specific timelines for completing an investigation of a claim, how should the responsible financial institution communicate the results to the account holder, and what steps can the account holder take if they disagree with the outcome?

**A.** The responsible financial institution must complete the investigation within 21 business days for straightforward cases or 45 business days for complex cases. The institution must then provide a written reply detailing the outcome and assessment of responsibility to the specified account holders. If an account holder disagrees with the assessment or if the claim falls outside the guidelines, they may pursue further action through existing dispute resolution avenues.

**Gold span** — Guidelines on Shared Responsibility Framework · clause 7.9

> The responsible FI, and responsible Telco where applicable, should complete an investigation of any relevant claim within 21 business days for straightforward cases or 45 business days for complex cases. 16 Complex cases may include cases where any party to the seemingly authorised transaction is overseas and uncontactable during the investigation period. Outcome Stage 7.10 The responsible FI should within the stipulated periods in paragraph 7.9 provide each account holder that the responsible FI has been instructed to send transaction notifications to in accordance with paragraph 3.1 17 of the EUPG, a written reply of the investigation outcome and the assessment of the account holder's responsibility. The responsible FI should seek acknowledgement, which need not be an agreement, from that account holder of the investigation outcome. Recourse Stage 7.11 Where the account holder does not

---

## gs-0018 · factual_lookup · confidence 1.0

**Q.** Under what circumstances does a Capital Markets Intermediary not need to inquire about beneficial owners for a customer?

**A.** A Capital Markets Intermediary is not required to inquire if there exists any beneficial owner when the customer is an entity listed and traded on the Singapore Exchange, an entity listed outside Singapore with adequate regulatory disclosure and transparency regarding beneficial owners, a financial institution listed in Appendix 1, a foreign financial institution supervised for AML/CFT consistent with FATF standards, or an investment vehicle managed by such institutions. However, this exemption does not apply if the CMI has doubts about the information's veracity or suspects links to money laundering or terrorism financing.

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.16

> A CMI shall not be required to inquire if there exists any beneficial owner in relation to a customer that is - (a) an entity listed and traded on the Singapore Exchange; (b) an entity listed on a stock exchange outside of Singapore that is subject to - (i) regulatory disclosure requirements; and (ii) requirements relating to adequate transparency in respect of its beneficial owners (imposed through stock exchange rules, law or other enforceable means); (c) a financial institution set out in Appendix 1; (d) a financial institution incorporated or established outside Singapore that is subject to and supervised for compliance with AML/CFT requirements consistent with standards set by the FATF; or (e) an investment vehicle where the managers are financial institutions 6 - (i) set out in Appendix 1; or (ii) incorporated or established outside Singapore but are subject to and supervised for c

---

## gs-0020 · factual_lookup · confidence 1.0

**Q.** What formatting requirement applies when submitting amendments to this form?

**A.** You must use the official template downloaded from MASNET and clearly mark any changes you make to the content of the form.

**Gold span** — Notice 130 on Insurance Returns (Accounts and Statements) for Captive Insurers · clause Instructions for completion of Form A7/1

> Insurers shall use the template of this Form downloaded from the MAS Network (MASNET) for completion. Any amendments made to the contents of this Form shall be clearly marked on the submitted Form. [MAS Notice 130 (Amendment No. 2) 2020]

---

## gs-0021 · factual_lookup · confidence 1.0

**Q.** What due diligence and risk management practices should banks apply when subscribing to a cloud service?

**A.** Banks are required to perform necessary due diligence and implement sound governance and risk management practices that align with the guidelines when they subscribe to a cloud service.

**Gold span** — Guidelines on Outsourcing (Banks) · clause 6

> The types of risks in CS that confront Banks are not distinct from that of other forms of outsourcing arrangements. Banks should perform the necessary due diligence and apply sound governance and risk management practices articulated in this set of Guidelines when subscribing to CS. 27 A cloud infrastructure operated solely for an organisation. 28 A cloud infrastructure made available to the general public or an industry group, and is owned by a third-party service provider.

---

## gs-0022 · factual_lookup · confidence 1.0

**Q.** How must a Digital Payment Token Service provider verify that its Customer Due Diligence data remains current?

**A.** The provider must ensure that CDD data, documents, and information are relevant and up-to-date by conducting reviews of existing records, with particular attention given to higher risk categories of customers.

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 6.31

> A payment service provider shall ensure that the CDD data, documents and information obtained in respect of customers, natural persons appointed to act on behalf of the customers, connected parties of the customers and beneficial owners of the customers, are relevant and kept up-to-date by undertaking reviews of existing CDD data, documents and information, particularly for higher risk categories of customers.

---

## gs-0023 · factual_lookup · confidence 1.0

**Q.** If the board delegates its responsibilities to a committee, what specific communication procedures must it establish?

**A.** The board should require the committee to report regularly and ensure that senior management is held accountable for implementation, while the board itself remains ultimately responsible for the committee's performance.

**Gold span** — Guidelines on Outsourcing (Banks) · clause 3.1.4

> Where the board delegates its responsibility to a committee as described in paragraph 3.1.2, the board should establish communication procedures between the board and the committee. This should include requiring the committee to report to the board on a regular basis, and ensuring that senior management is held responsible for implementation of the expectations in these Guidelines as elaborated in paragraph 3.1.3. Notwithstanding the delegation of responsibility to a committee, the board shall remain responsible for the performance of its responsibilities by that committee.

---

## gs-0024 · factual_lookup · confidence 1.0

**Q.** How must a licensee inform its customers and potential customers about its normal business days and hours and any changes to them?

**A.** A licensee must notify all relevant parties in writing by publishing the information in publicly available materials and displaying it prominently so that customers can see it before using the digital token service.

**Gold span** — MAS Notice FSM-N32 Conduct · clause 15

> A licensee must notify all its customers and potential customers in writing of its normal business days and hours and any changes to its normal business days and hours by: (a) publishing the notification in publicly available material; and (b) displaying prominently the notification such that a customer or potential customer would have notice of such information prior to using the digital token service provided by the licensee. Obligation of licensee to notify Authority of certain events

---

## gs-0025 · factual_lookup · confidence 1.0

**Q.** What specific components must an institution include in its liquidity risk stress testing programs to ensure effective contingency funding plans?

**A.** An institution must incorporate a range of both short-term and long-term scenarios that are specific to itself as well as market-wide factors, utilizing conservative assumptions that are reviewed on a regular basis. The results from these tests should then be used to adjust the institution's liquidity risk management strategies, policies, positions, and to develop effective contingency funding plans.

**Gold span** — Guidelines on Risk Management Practices – Liquidity Risk · clause 3.6

> An institution should include a variety of short-term and protracted institution-specific and market-wide liquidity stress scenarios (individually and in combination), using conservative and regularly reviewed assumptions, into its stress testing programmes for risk management purposes. The results of the stress tests should be used by the institution to adjust its liquidity risk management strategies, policies and positions and to develop effective contingency funding plans.

---

## gs-0027 · factual_lookup · confidence 1.0

**Q.** What due diligence processes should a bank apply when considering, renegotiating, or renewing an outsourcing arrangement?

**A.** A bank must subject the service provider to appropriate due diligence processes to assess the risks associated with the outsourcing arrangements.

**Gold span** — Guidelines on Outsourcing (Banks) · clause 3.3.1

> In considering, renegotiating or renewing an outsourcing arrangement, a Bank should subject the service provider to appropriate due diligence processes to assess the risks associated with the outsourcing arrangements.

---

## gs-0028 · factual_lookup · confidence 1.0

**Q.** If a reporting bank uses multiple credit risk measurement models for one exposure, how must it calculate the risk-weighted amount?

**A.** The bank must split the exposure into separate portions based on each model and calculate the credit risk-weighted amount for each portion individually.

**Gold span** — Notice 637 Risk Based Capital Adequacy Requirements for Banks Incorporated in Singapore · clause Section 1: General Requirements/1.2

> A Reporting Bank must keep, for 5 years, and make available at the request of the Authority, a record of the review mentioned in paragraph 1.1(b) of this Annex. 1.3 Where a Reporting Bank uses multiple CRM for a single exposure, the Reporting Bank must sub-divide the exposure into portions covered by each CRM 403 and must calculate the credit risk-weighted exposure amount of each portion separately. A Reporting Bank must apply the same approach when recognising eligible credit protection by a single protection provider where the eligible credit protection has differing maturities.

---

## gs-0029 · factual_lookup · confidence 1.0

**Q.** Who retains responsibility for managing outsourcing risks even when day-to-day duties are delegated to a service provider?

**A.** The institution, its board, and senior management must maintain effective oversight, governance, and risk management frameworks regardless of delegation.

**Gold span** — ​Guidelines on Outsourcing [Cancelled] · clause 5.2

> 5.2.1 The board and senior management of an institution play pivotal roles in ensuring a sound risk management culture and environment. While an institution may delegate day-today operational duties to the service provider, the responsibilities for maintaining effective oversight and governance of outsourcing arrangements, managing outsourcing risks, and implementing an adequate outsourcing risk management framework, in accordance with these Guidelines, continue to rest with the institution, its board and senior management. The board and senior management of an institution should ensure there are adequate processes to provide a comprehensive institution-wide view of the institution's risk exposures from outsourcing, and incorporate the assessment and mitigation of such risks into the institution's outsourcing risk management framework.

---

## gs-0030 · factual_lookup · confidence 1.0

**Q.** What checks must a direct insurer perform before granting a credit facility for residential property purchase?

**A.** A direct insurer must conduct comprehensive checks with credit bureaus and the HDB to verify if the borrower has outstanding facilities for other residential properties, assess their creditworthiness, and comply with specific regulatory paragraphs. If the borrower provides credible third-party information, the insurer may use it to supplement bureau data when necessary.

**Gold span** — Notice 115 Residential Property Loans · clause 7

> Prior to the grant of a credit facility for the purchase of Residential Property, a direct insurer must conduct or cause to be conducted comprehensive checks with one or more credit bureaus and the HDB, as may be relevant, on the information held by such parties - (a) to verify whether the Borrower, at the time of applying for the credit facility, has any outstanding credit facility for the purchase of any other Residential Property; (b) to comply with paragraphs 2 and 5; and (c) to assess the credit worthiness of the Borrower, and where the Borrower reasonably satisfies the direct insurer that the direct insurer should take into account additional information in order to ascertain whether or not the Borrower has an outstanding credit facility for the purchase of any other Residential Property, or whether or not the Borrower is credit worthy, the direct insurer may supplement the informa

---

## gs-0033 · factual_lookup · confidence 1.0

**Q.** What specific actions must a bank take if it reasonably suspects its current customer relationship involves money laundering or terrorism financing but decides to keep the customer?

**A.** If a bank chooses to retain a customer despite reasonable grounds for suspicion of money laundering or terrorism financing, it must document the reasons for that decision and apply commensurate risk mitigation measures, which include enhanced ongoing monitoring.

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 6.25

> Where there are any reasonable grounds for suspicion that existing business relations with a customer are connected with money laundering or terrorism financing, and where the bank considers it appropriate to retain the customer - (a) the bank shall substantiate and document the reasons for retaining the customer; and (b) the customer's business relations with the bank shall be subject to commensurate risk mitigation measures, including enhanced ongoing monitoring.

---

## gs-0034 · factual_lookup · confidence 1.0

**Q.** When performing customer due diligence for a Variable Capital Company that uses a distributor to market its fund, under what conditions can the VCC rely on the distributor's identification of underlying investors instead of conducting its own inquiry?

**A.** A Variable Capital Company may rely on a distributor's customer due diligence measures regarding underlying investors if the distributor is a financial institution supervised by the Monetary Authority of Singapore for anti-money laundering compliance. If these conditions are not met, the VCC must perform appropriate due diligence on the underlying investors itself or apply simplified measures where applicable.

**Gold span** — Guidelines to Notice VCC-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies · clause 2

> Connected Party 2-1 The term 'partnership' as it appears in the definition of 'connected party' includes foreign partnerships. The term 'manager' as it appears in limb (b) of the definition of 'connected party' takes reference from section 2(1) of the Limited Liability Partnerships Act 2005 and section 28 of the Limited Partnerships Act 2008. 2-2 Examples of natural persons with executive authority in a company include the Chairman and Chief Executive Officer. An example of a natural person with executive authority in a partnership is the Managing Partner. Customer 2-3 When performing Customer Due Diligence ('CDD') measures in the scenarios below, the following approaches may be adopted: (a) Engagement of Distributors A distributor may have been engaged to market a VCC's fund(s), and may use omnibus accounts in its own name to transact in or subscribe to units or shares in the VCC on beh

---

## gs-0035 · factual_lookup · confidence 1.0

**Q.** What specific steps must a finance company take to satisfy the requirements for appropriate risk management?

**A.** A finance company must document its risk assessments, consider all relevant factors before setting overall risk levels and mitigation strategies, keep these assessments current, and maintain mechanisms to share this information with the Authority.

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 4.2

> The appropriate steps referred to in paragraph 4.1 shall include - (a) documenting the finance company's risk assessments; (b) considering all the relevant risk factors before determining the level of overall risk and the appropriate type and extent of mitigation to be applied; (c) keeping the finance company's risk assessments up -to-date; and (d) having appropriate mechanisms to provide its risk assessment information to the Authority. Risk Mitigation

---

## gs-0036 · factual_lookup · confidence 1.0

**Q.** What measures must a finance company take when relying on a third party to perform customer due diligence?

**A.** A finance company can rely on a third party's CDD if the third party has an existing independent relationship with the customer and performs its own checks under its own AML/CFT rules. The finance company may satisfy requirements by reviewing public assessments, examining foreign laws for comparability, obtaining professional advice, or reviewing the third party's policies.

**Gold span** — Guidelines to MAS Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism - Finance Companies · clause 9

> 9-1 Paragraph 9 does not apply to outsourcing. Third party reliance under paragraph 9 of the Notice is different from an outsourcing arrangement or agreement. 9-2 In a third party reliance scenario, the third party will typically have an existing relationship with the customer that is independent of the relationship to be formed by the customer with the relying finance company. The third party will therefore perform the CDD measures on the customer according to its own AML/CFT policies, procedures and controls. 9-3 In contrast to a third party reliance scenario, the outsourced service provider performs the CDD measures (e.g. performs centralised transaction monitoring functions) on behalf of the finance company, in accordance with the finance company's AML/CFT policies, procedures and standards, and is subject to the finance company's control measures to effectively implement the finance

---

## gs-0037 · factual_lookup · confidence 1.0

**Q.** What identification and recording steps must a merchant bank complete before executing a wire transfer?

**A.** Before effecting a wire transfer, every merchant bank that acts as an ordering institution must identify and verify the originator's identity if not already done previously, and record sufficient details such as the date, currency type and amount, and value date to allow reconstruction of the transaction.

**Gold span** — Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks · clause 11.3

> Before effecting a wire transfer, every merchant bank that is an ordering institution shall - (a) identify the wire transfer originator and verify the wire transfer originator's identity, as the case may be (if the merchant bank has not already done so by virtue of paragraph 6); and (b) record adequate details of the wire transfer so as to permit its reconstruction, including but not limited to, the date of the wire transfer, the type and amount of currency transferred and the value date. (II) Cross-Border Wire Transfers Below or Equal To S$1,500

---

## gs-0038 · factual_lookup · confidence 1.0

**Q.** How should these Guidelines be read in relation to relevant legislation?

**A.** These Guidelines are not intended to replace legislative provisions and must be read alongside them, as well as any other written directions, codes, or guidelines issued by MAS.

**Gold span** — E-Payments User Protection Guidelines · clause 1.4

> These Guidelines provide general guidance, and are not intended to be comprehensive nor replace or override any legislative provisions. They should be read in conjunction with the provisions of the relevant legislation, the subsidiary legislation made under the relevant legislation, as well as written directions, notices, codes and other guidelines that MAS may issue from time to time pursuant to the relevant legislation and subsidiary legislation.

---

## gs-0039 · factual_lookup · confidence 1.0

**Q.** What specific due diligence steps must a Singapore finance company undertake when onboarding a new respondent financial institution for correspondent banking?

**A.** A finance company must assess the suitability of the respondent institution by gathering adequate information about its business, determining its reputation and supervision quality, and evaluating its AML/CFT controls. Additionally, it must document respective responsibilities and obtain senior management approval before providing services to the new institution.

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 10.3

> A finance company in Singapore shall perform the following measures, in addition to the measures as required by paragraphs 6, 7 and 8, when providing correspondent banking or other similar services: (a) assess the suitability of the respondent financial institution by taking the following steps: (i) gather adequate information about the respondent financial institution to understand fully the nature of the respondent financial institution's business, including making appropriate inquiries on its management, its major business activities and the countries or jurisdictions in which it operates; (ii) determine from any available sources the reputation of the respondent financial institution and the quality of supervision over the respondent financial institution, including whether it has been the subject of money laundering or terrorism financing investigation or regulatory action; and (iii

---

## gs-0041 · factual_lookup · confidence 1.0

**Q.** Before processing a wire transfer, what specific identity verification and record-keeping actions must an ordering institution classified as a Specified Payment Services entity perform?

**A.** The institution must identify the originator of the transfer and take reasonable steps to verify their identity. It also needs to record sufficient details to allow for reconstruction of the transaction, such as the date, currency type and amount, and value date.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 15.3

> Before effecting or arranging for a wire transfer, every payment service provider that is an ordering institution shall ⎯ (a) identify the wire transfer originator and take reasonable measures to verify the wire transfer originator's identity , as the case may be (if the payment service provider has not already done so by virtue of paragraph 7); and (b) record adequate details of the wire transfer so as to permit its reconstruction, including but not limited to, the date of the wire transfer, the type and amount of currency transferred and the value date. (II) Cross-Border Wire Transfers Below or Equal To S$1,500

---

## gs-0042 · factual_lookup · confidence 1.0

**Q.** How does a depository's adherence to these guidelines affect its risk assessment?

**A.** The degree of observance with these Guidelines by the Depository may have an impact on the Authority's overall risk assessment of the Depository, including the quality of its board and senior management oversight, governance, internal controls and risk management.

**Gold span** — Guidelines to Notice SFA 03AA-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 1

> 1-1 These Guidelines provide guidance to the Depository on the requirements in MAS Notice SFA03AA-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism - the Depository ('the Notice'). These Guidelines should be read in conjunction with the Notice. 1-2 The expressions used in these Guidelines have the same meanings as those found in the Notice, except where expressly defined in these Guidelines or where the context otherwise requires. For the purposes of these Guidelines, a reference to 'CDD measures' shall mean the measures as required by paragraphs 6, 7 and 8 of the Notice. 1-3 The degree of observance with these Guidelines by the Depository may have an impact on the Authority's overall risk assessment of the Depository, including the quality of its board and senior management oversight, governance, internal controls and risk management. 1-4 Key Concepts Money

---

## gs-0043 · factual_lookup · confidence 1.0

**Q.** What specific laws and regulations must a Financial Institution Dealing In Precious Stones And Precious Metals consider when implementing enhanced customer due diligence for higher-risk situations?

**A.** The institution must ensure its enhanced measures align with all laws, regulations, or directions administered by the Authority. This specifically includes requirements under section 192 read with section 15(1)(b) of the FSM Act and section 15(1)(a) of the FSM Act.

**Gold span** — Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · clause 8.8

> A financial institution shall, in taking enhanced CDD measures to manage and mitigate any higher risks that have been identified by the financial institution, or notified to it by the Authority or other relevant authorities in Singapore, ensure that the enhanced CDD measures take into account the requirements of any laws, regulations or directions administered by the Authority, including but not limited to the regulations or directions issued by the Authority under section 192 read with section 15(1)(b) of the FSM Act, and section 15(1)(a) of the FSM Act.

---

## gs-0044 · factual_lookup · confidence 1.0

**Q.** What specific measures can a financial adviser take when satisfied that money laundering and terrorism financing risks are low?

**A.** When risks are deemed low, an adviser may reduce how often customer information is updated, lower the intensity of ongoing transaction scrutiny based on set monetary limits, or infer the purpose of business relations from transaction types rather than collecting explicit details.

**Gold span** — Guidelines to Notice FAA-N06 on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 7

> 7-1 Paragraph 7.1 of the Notice permits a financial adviser to adopt a risk-based approach in assessing the necessary measures to be performed, and to perform appropriate SCDD measures in cases where the financial adviser is satisfied, upon analysis of risks, that the ML/TF risks are low. 7-2 Where a financial adviser applies SCDD measures, it is still required to perform ongoing monitoring of business relations under the Notice. 7-3 Under SCDD, a financial adviser may adopt a risk-based approach in assessing whether any measures should be performed for connected parties of the customer. 7-4 Where a financial adviser is satisfied that the risks of money laundering and terrorism financing are low, a financial adviser may perform SCDD measures. Examples of possible SCDD measures include - (a) reducing the frequency of updates of customer identification information; (b) reducing the degree

---

## gs-0045 · factual_lookup · confidence 1.0

**Q.** What measures must a Depository be satisfied about regarding a respondent financial institution's relationship with a third party that has direct access to a payable-through account?

**A.** The Depository must confirm that the respondent financial institution has implemented appropriate safeguards for the third party, can continuously monitor its business relationship with that party, and is prepared to provide customer due diligence information when asked.

**Gold span** — Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 10.4

> Where the correspondent account services involve a payable-through account, the Depository shall be satisfied that - (a) the respondent financial institution has performed appropriate measures at least equivalent to those specified in paragraph 6 on the third party having direct access to the payable-through account; and (b) the respondent financial institution is able to perform ongoing monitoring of its business relations with that third party and is willing and able to provide CDD information to the Depository upon request.

---

## gs-0046 · multi_hop · confidence 1.0

**Q.** If a Digital Payment Token Service provider operates in a jurisdiction where the FATF has called for countermeasures, can it still rely on an analysis showing low money laundering and terrorism financing risks to apply simplified customer due diligence measures?

**A.** No, because a service provider is prohibited from applying simplified measures if any of its customers or beneficial owners are located in a jurisdiction subject to FATF countermeasures, regardless of the risk assessment outcome.

**Gold span** — Guidelines to Notice PSN02 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Payment Token Service · clause 7

> 7-1 Paragraph 7.1 of the Notice permits a payment service provider to adopt a riskbased approach in assessing the necessary measures to be performed, and to perform appropriate SCDD measures, in cases where the payment service provider is satisfied, upon analysis, that the ML/TF risks are low. 7-2 Where a payment service provider applies SCDD measures, it is still required to perform ongoing monitoring of business relations and reviews of transactions undertaken without an account being opened, under the Notice. In addition, to ensure compliance with applicable laws and regulations in Singapore, including the FSM Sanctions Regulations relating to sanctioned parties, a payment service provider is reminded that where it applies SCDD measures, it is still required to screen all parties under the Notice. 7-3 Under SCDD, a payment service provider may adopt a risk-based approach in assessing

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 7.4

> A payment service provider shall not perform simplified CDD measures ⎯ (a) where one or more transactions undertaken, whether in the course of business relations or otherwise, by the payment service provider for a customer in any one year period cumulatively exceeds S$20,000 6 ; (b) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction in relation to which the FATF has called for countermeasures; (c) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction known to have inadequate AML/CFT measures, as determined by the payment service provider for itself, or notified to payment service providers generally by the Authority, or other foreign regulatory authorities; or (d) where the payment service provider suspects that money laundering or terrorism financing is involved.

---

## gs-0047 · multi_hop · confidence 1.0

**Q.** What specific obligations do banks have regarding information received through COSMIC when conducting risk assessments for new business relations or linked transactions?

**A.** Banks must consider relevant information received through COSMIC, including past risk assessment results, when performing required measures. They should also pay attention to whether such information triggers specific suspicion scenarios and perform the necessary measures accordingly.

**Gold span** — Guidelines to Notice 626 on Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 6

> 6-A Banks participating in COSMIC 6-A-1 Where relevant, a bank participating in COSMIC should take into consideration the information it has received through COSMIC, including the results of any risk assessments it has performed under MAS Notice FSM-N02 on 'Prevention of Money Laundering and Countering the Financing of Terrorism - Financial Institutions' Information Sharing Platform' ('MAS Notice FSM-N02'), when performing the risk mitigation measures under paragraphs 6, 7, and 8 of the Notice. For the avoidance of doubt, when performing such measures when establishing new business relations with a customer, the bank need not consider any information that is no longer available in COSMIC (e.g. Listings (as defined in MAS Notice FSM-N02) which are no longer available in COSMIC at the time of establishing new business relations with that customer). Notice Paragraph 6.2 6-1 Where There Are

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 7

> Persons exempted under section 99(1)(h) of the SFA read with paragraph 7(1)(b) of the Second Schedule to the Securities and Futures (Licensing and Conduct of Business) Regulations (Rg. 10). [MAS Notice 626 (Amendment) 2025]

---

## gs-0048 · multi_hop · confidence 1.0

**Q.** For a bank dealing with an investment vehicle where the managers are financial institutions incorporated outside Singapore, under what specific conditions can it avoid performing CDD on the underlying investors?

**A.** A bank is not required to identify or verify the underlying investors if the managing financial institution is subject to AML/CFT standards consistent with FATF requirements, unless the bank has doubts about the information provided or suspects money laundering or terrorism financing.

**Gold span** — Guidelines to Notice 626 on Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 2

> Connected Party 2-1 The term 'partnership' as it appears in the definition of 'connected parties' includes foreign partnerships. The term 'manager' as it appears in limb (b) of the definition of 'connected parties' takes reference from section 2(1) of the Limited Liability Partnerships Act 2005 and section 28 of the Limited Partnerships Act 2008. 2-2 Examples of natural persons with executive authority in a company include the Chairman and Chief Executive Officer. An example of a natural person with executive authority in a partnership is the Managing Partner. Customer 2-3 When performing Customer Due Diligence ('CDD') measures in the scenarios below, the following approaches may be adopted: (a) Portfolio Managers A bank may encounter cases where, to its knowledge, the customer is a manager of a portfolio of assets and who is operating the account in that capacity. In such cases, the und

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 6.16

> A bank shall not be required to inquire if there exists any beneficial owner in relation to a customer that is - (a) an entity listed and traded on the Singapore Exchange; (b) an entity listed on a stock exchange outside of Singapore that is subject to - (i) regulatory disclosure requirements; and (ii) requirements relating to adequate transparency in respect of its beneficial owners (imposed through stock exchange rules, law or other enforceable means); (c) a financial institution set out in Appendix 1; (d) a financial institution incorporated or established outside Singapore that is subject to and supervised for compliance with AML/CFT requirements consistent with standards set by the FATF; or (e) an investment vehicle where the managers are financial institutions 6 - (i) set out in Appendix 1; or (ii) incorporated or established outside Singapore but are subject to and supervised for

---

## gs-0049 · multi_hop · confidence 1.0

**Q.** For which specific customers must a Digital Token Service Provider perform enhanced CDD measures because they are identified as presenting higher risk?

**A.** A Digital Token Service Provider must apply enhanced customer due diligence measures to any customer it determines presents a higher risk for money laundering or terrorism financing, or whose status is notified by the Authority.

**Gold span** — Guidelines to MAS Notice FSM-N27 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Token Service Providers · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, a digital token service provider shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.7 of the Notice include - (a) Customer risk (i) customers from higher risk businesses/ activities/ sectors identified in Singapore's NRA, guidance from the Authority, as well as other higher risk businesses/ activities/ sectors identified by the digital token service provider; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relations with a customer or transactions undertaken without an account being opened that are conducted under

**Gold span** — MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · clause 8.7

> A digital token service provider must perform the appropriate enhanced CDD measures in paragraph 8.3 for business relations with, or transactions for a customer ⎯ (a) who the digital token service provider determines under paragraph 8.5; or (b) the Authority or other relevant authorities in Singapore notify to the digital token service provider, as presenting a higher risk for money laundering or terrorism financing.

---

## gs-0050 · multi_hop · confidence 1.0

**Q.** For a Digital Payment Token Service Provider conducting its first non-face-to-face business contact with a customer, what specific external assessment must be appointed to evaluate the effectiveness of policies regarding impersonation risks?

**A.** The provider must appoint an external auditor or an independent qualified consultant at its own expense to assess the effectiveness of the policies and procedures related to impersonation risks.

**Gold span** — Guidelines to Notice PSN02 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Payment Token Service · clause 6

> Notice Paragraph 6.2 6-1 Where There are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations or Undertaking any Transaction without Opening an Account 6-1-1 In arriving at its decision for each case, a payment service provider should take into account the relevant facts, including information that may be made available by the authorities, and conduct a proper risk assessment. Notice Paragraphs 6.3 to 6.4 6-2 When CDD is to be Performed and Linked Transactions 6-2-1 Two or more transactions may be related or linked if they involve the same sender or recipient. A payment service provider should be aware that transactions may be entered into consecutively, with the intention of circumventing applicable thresholds set out in the Notice. Notice Paragraphs 6.5 to 6.18 6-3 CDD Measures under Paragraphs 6.5 to 6.18 6-3-1 When relying on documents, a payment service

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 6.37

> Where a payment service provider conducts its first non-face-to-face business contact, the payment service provider shall, at the payment service provider's own expense, appoint an external auditor or an independent qualified consultant to assess the effectiveness of the policies and procedures referred to in paragraph 6.34, including the effectiveness of any technology solutions used to manage impersonation risks.

---

## gs-0051 · multi_hop · confidence 1.0

**Q.** When are Approved Trustees required to apply enhanced due diligence measures for customers originating from higher-risk sectors?

**A.** Approved Trustees must apply enhanced due diligence when they identify ML/TF risks as higher, specifically for customers falling into categories such as those from high-risk jurisdictions or sectors, complex ownership structures, or exhibiting characteristics of shell companies.

**Gold span** — Guidelines to Notice SFA 13-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism - Approved Trustees · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, an approved trustee shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.7 of the Notice include - (a) Customer risk (i) customers from higher risk businesses / activities / sectors identified in Singapore's NRA, as well as other higher risk businesses / activities / sectors identified by the approved trustee; (ii) the ownership structure of the legal person appears unusual or excessively complex given the nature of the legal person's business; (iii) legal persons that are personal asset holding vehicles; (iv) the business relation is conducted under unusual circumstances (e.g. significant unexplained geographic distance between the approved trustee and the customer); (v) companies that have nominee shareholders or shares in bearer form; (vi

**Gold span** — Notice SFA 13-N01 to Approved Trustees on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 8.1

> For the purposes of paragraph 8 ⎯ 'close associate' means a natural person who is closely connected to a politically exposed person, either socially or professionally; 'domestic politically exposed person' means a natural person who is or has been entrusted domestically with prominent public functions; 'family member' means a parent, step-parent, child, step-child, adopted child, spouse, sibling, step-sibling, and adopted sibling of the politically exposed person; 'foreign politically exposed person' means a natural person who is or has been entrusted with prominent public functions in a foreign country or jurisdiction; 'international organisation' mean s an entity established by formal political agreements between member countries or jurisdictions that have the status of international treaties, whose existence is recognised by law in member countries or jurisdictions and which is not tr

---

## gs-0052 · multi_hop · confidence 1.0

**Q.** What specific ML/TF risk assessment requirements apply to Variable Capital Companies regarding new technologies, and what level of governance must approve these assessments?

**A.** Variable Capital Companies must conduct a separate assessment of money laundering and terrorist financing risks associated with new products, practices, or technologies that handle customer funds, distinct from other standard risks. These specific assessments require approval from either senior management or the company's board of directors.

**Gold span** — Guidelines to Notice VCC-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies · clause 6

> 6-1 International developments of new technologies and payment methods in the provision of financial services are fast-changing and growing at an accelerated pace. A VCC should keep abreast of such new developments and the ML/TF risks associated with them. 6-2 An assessment of the VCC's ML/TF risks in relation to new products, practices and technologies is separate from, and in addition to, the assessment of other risks such as credit risks, operational risks or market risks. For example, in the assessment of ML/TF risks, attention should be given to new products, practices and technologies that deal with customer funds or the movement of such funds. These assessments should be approved by senior management or the VCC's board of directors. 6-3 An example of a 'delivery mechanism' as set out in paragraph 6 of the Notice is mobile trading.

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 6

> Persons exempted under section 20(1)(g) of the Financial Advisers Act 2001 read with regulation 27(1)(d) of the Financial Advisers Regulations (Rg. 2) except those which only provide advice by issuing or promulgating research analyses or research reports, whether in electronic, print or other form, concerning any investment product. [MAS Notice VCC-N01 (Amendment) 2022] [MAS Notice VCC-N01 (Amendment) 2025]

---

## gs-0053 · multi_hop · confidence 1.0

**Q.** For a direct life insurer dealing with an unfamiliar customer who is a financial institution incorporated outside Singapore subject to FATF standards, are they still required to verify the identity of that customer's beneficial owners despite general exceptions for such entities?

**A.** A direct life insurer is not generally required to inquire about beneficial owners for a foreign financial institution supervised under FATF standards, unless it has doubts regarding the information or suspects money laundering or terrorism financing.

**Gold span** — Guidelines to MAS Notice 314 Notice on Prevention of Money Laundering and Countering the Financing of Terrorism – Life Insurers · clause 6

> Notice Paragraph 6.2 6-1 Where There Are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations 6-1-1 In arriving at its decision for each case, a direct life insurer should take into account the relevant facts, including information that may be made available by the authorities and conduct a proper risk assessment. Notice Paragraphs 6.4 to 6.22 6-2 CDD Measures under Paragraphs 6.4 to 6.22 6-2-1 When relying on documents, a direct life insurer should be aware that the best documents to use to verify the identity of the customer are those most difficult to obtain illicitly or to counterfeit. These may include government issued identity cards or passports, reports from independent company registries, published or audited annual reports and other reliable sources of information. The rigour of the verification process should be commensurate with the customer's ris

**Gold span** — Notice 314 Prevention of Money Laundering and Countering the Financing of Terrorism – Life Insurers · clause 6.19

> A direct life insurer shall not be required to inquire if there exists any beneficial owner in relation to, a customer or a beneficiary that is - (a) an entity listed and traded on the Singapore Exchange; (b) an entity listed on a stock exchange outside of Singapore that is subject to - (i) regulatory disclosure requirements; and (ii) requirements relating to adequate transparency in respect of its beneficial owners (imposed through stock exchange rules, law or other enforceable means); (c) a financial institution set out in Appendix 1; (d) a financial institution incorporated or established outside Singapore that is subject to and supervised for compliance with AML/CFT requirements consistent with standards set by the FATF; or (e) an investment vehicle where the managers are financial institutions 6 - (i) set out in Appendix 1; or (ii) incorporated or established outside Singapore but a

---

## gs-0057 · multi_hop · confidence 1.0

**Q.** For a Specified Payment Service provider assessing a customer from a jurisdiction subject to FATF countermeasures, what specific risk classification must they apply, and how does this relate to the broader internal risk management systems required for identifying higher risk customers?

**A.** The provider must treat any business relations or transactions with such a customer as presenting a higher risk for money laundering or terrorism financing. This requirement is one of the specific circumstances that fall under the implementation of appropriate internal risk management systems used to determine which customers present a higher risk.

**Gold span** — FSM-N01 Notice on Submission of Returns by Notified Entities · clause Instructions for completion of Form C/6

> 'Higher risk customers' in paragraph 8 refers to custo mers that are determined by a Notified Entity from its implementation of appropriate internal risk management systems, policies, procedures and controls in accordance with paragraph 9.6 of MAS Notice PS-N01 to present a higher risk for money laundering or terrorism financing, including but not limited to customers described in paragraphs 9.7 of MAS Notice PSN01 and a 'politically exposed person', or a 'family member' or 'close associate' of a 'politically exposed person' within the meaning of paragraph 9.1 of MAS Notice PS-N01.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 9.7

> For the purposes of paragraph 9.6, circumstances where a customer presents or may present a higher risk for money laundering or terrorism financing include but are not limited to the following: (a) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction in relation to which the FATF has called for countermeasures, the payment service provider shall treat any business relations with or transactions (except for specified money-changing transactions) for any such customer as presenting a higher risk for money laundering or terrorism financing; (b) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction known to have inadequate AML/CFT measures, as determined by the payment service provider for itself, or notified to payment service providers generally by the Authority or other foreign regulatory authorities, t

---

## gs-0058 · multi_hop · confidence 1.0

**Q.** What specific policies must a Digital Token Service Provider develop to handle non-face-to-face business contacts, and which types of documents should they prioritize when verifying a customer's identity under those circumstances?

**A.** A Digital Token Service Provider must develop policies to address risks associated with non-face-to-face business relations. When verifying identity, they should prioritize using documents that are most difficult to obtain illicitly, counterfeit, or falsify digitally, such as government-issued identity cards or passports.

**Gold span** — Guidelines to MAS Notice FSM-N27 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Token Service Providers · clause 6

> Notice Paragraph 6.2 6-1 Where There are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations or Undertaking any Transaction without Opening an Account 6-1-1 In arriving at its decision for each case, a digital token service provider should take into account the relevant facts, including information that may be made available by the authorities, and conduct a proper risk assessment. Notice Paragraphs 6.3 to 6.4 6-2 When CDD is to be Performed and Linked Transactions 6-2-1 Two or more transactions may be related or linked if they involve the same sender or recipient. A digital token service provider should be aware that transactions may be entered into consecutively, with the intention of circumventing applicable thresholds set out in the Notice. Notice Paragraphs 6.5 to 6.22 6-3 CDD Measures under Paragraphs 6.5 to 6.22 6-3-1 When relying on documents, a digi

**Gold span** — MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.39

> A digital token service provider must develop policies and procedures to address specific risks associated with non-face-to-face business relations with a customer or non-face-toface transactions undertaken without an account being opened for a customer ('non -facetoface business contact').

---

## gs-0059 · multi_hop · confidence 1.0

**Q.** When a Capital Markets Intermediary identifies higher ML/TF risks in a customer relationship, what specific legal requirements must their enhanced due diligence measures satisfy?

**A.** The CMI must ensure that its enhanced due diligence measures comply with any laws, regulations, or directions administered by the Authority, including those under the FSM Act.

**Gold span** — Guidelines to Notice SFA 04-N02 on Prevention of Money Laundering and Countering the Financing of Terrorism - Capital Markets Intermediaries · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, a CMI shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.7 of the Notice include - (a) Customer risk (i) customers from higher risk businesses / activities / sectors identified in Singapore's NRA, as well as other higher risk businesses / activities / sectors identified by the CMI; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relation is conducted under unusual circumstances (e.g. significant unexplained geographic distance between the CMI and the customer); (v) companies that have nominee shareholders or shares

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 8.8

> A CMI shall, in taking enhanced CDD measures to manage and mitigate any higher risks that have been identified by the CMI, or notified to it by the Authority or other relevant authorities in Singapore, ensure that the enhanced CDD measures take into account the requirements of any laws, regulations or directions administered by the Authority, including but not limited to the regulations or directions issued by the Authority under section 192 read with section 15(1)(b) of the FSM Act, and section 15(1)(a) of the FSM Act, respectively.

---

## gs-0061 · multi_hop · confidence 1.0

**Q.** If a Depository believes that carrying out standard anti-money laundering steps would alert a customer to their investigation, what specific actions are permitted regarding those steps and what additional reporting obligation must be fulfilled immediately?

**A.** The institution may stop performing the measures but must document the justification for this decision and file a suspicious transaction report without delay.

**Gold span** — Guidelines to Notice SFA 03AA-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 13

> 13-A The detection and investigation of concerns of higher ML/TF risks, even before suspicions of ML/TF are raised, can facilitate the early imposition of ML/TF risk mitigation measures. In this regard, the Depository should ensure that processes are in place to: (a) identify and prioritise the review of concerns of higher ML/TF risks; (b) ensure that such concerns of higher ML/TF risks are reviewed promptly; and (c) require any such concerns of higher ML/TF risks that cannot be reviewed promptly to be escalated to senior management, or a similar oversight body, for the application of appropriate ML/TF risk mitigation measures. 13-1 The Depository should ensure that the internal process for evaluating whether a matter should be referred to the Suspicious Transaction Reporting Office ('STRO') via an STR is completed without delay. The filing of an STR should not exceed 5 business days aft

**Gold span** — Notice SFA 03AA-N01 to the Depository on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 13.4

> Where the Depository forms a suspicion of money laundering or terrorism financing, and reasonably believes that performing any of the measures as required by paragraphs 6, 7 or 8 will tip-off a customer, a natural person appointed to act on behalf of the customer or a connected party of the customer, or a beneficial owner of the customer, the Depository may stop performing those measures, shall document the basis for its assessment and file an STR.

---

## gs-0062 · multi_hop · confidence 1.0

**Q.** For a Digital Token Service Provider that has determined low money laundering and terrorism financing risks through adequate analysis, under what specific financial thresholds or circumstances involving FATF countermeasures or jurisdictional risk assessments is it prohibited from applying simplified customer due diligence measures?

**A.** A Digital Token Service Provider must not apply simplified customer due diligence measures if cumulative transactions for a customer exceed S$20,000 in any one year period, if the customer or beneficial owner is from a country subject to FATF countermeasures or known for inadequate anti-money laundering controls, or if there is suspicion of money laundering or terrorism financing.

**Gold span** — Guidelines to MAS Notice FSM-N27 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Token Service Providers · clause 7

> 7-1 Paragraph 7.1 of the Notice permits a digital token service provider to adopt a riskbased approach in assessing the necessary measures to be performed, and to perform appropriate SCDD measures, in cases where the digital token service provider is satisfied, upon analysis, that the ML/TF risks are low. 7-2 Where a digital token service provider applies SCDD measures, it is still required to perform ongoing monitoring of business relations and reviews of transactions undertaken without an account being opened, under the Notice. In addition, to ensure compliance with applicable laws and regulations in Singapore, including the FSM Sanctions Regulations relating to sanctioned parties, a digital token service provider is reminded that where it applies SCDD measures, it is still required to screen all parties under the Notice. 7-3 Under SCDD, a digital token service provider may adopt a ris

**Gold span** — MAS Notice FSM-N27 Prevention of Money Laundering and Countering the Financing of Terrorism · clause 7.4

> A digital token service provider must not perform simplified CDD measures ⎯ (a) if one or more transactions undertaken, whether in the course of business relations or otherwise, by the digital token service provider for a customer in any one year period cumulatively exceeds S$20,000 6 ; (b) if a customer or a beneficial owner of the customer is from or in a country or jurisdiction in relation to which the FATF has called for countermeasures; (c) if a customer or a beneficial owner of the customer is from or in a country or jurisdiction known to have inadequate AML/CFT measures, as determined by the digital token service provider for itself, or notified to digital token service providers generally by the Authority, or other foreign regulatory authorities; or (d) if the digital token service provider suspects that money laundering or terrorism financing is involved.

---

## gs-0063 · multi_hop · confidence 1.0

**Q.** If a Capital Markets Intermediary acts as a primary manager for an investment vehicle managed by another entity, when must they inquire about the beneficial owners of that fund?

**A.** The Capital Markets Intermediary is required to inquire about the beneficial owners unless the underlying investors are distributed by a financial institution or are themselves supervised entities meeting specific standards, provided there are no suspicions of money laundering or terrorism financing.

**Gold span** — Guidelines to Notice SFA 04-N02 on Prevention of Money Laundering and Countering the Financing of Terrorism - Capital Markets Intermediaries · clause 2

> Connected Party 2-1 The term 'partnership' as it appears in the definition of 'connected parties' includes foreign partnerships. The term 'manager' as it appears in limb (b) of the definition of 'connected parties' takes reference from section 2(1) of the Limited Liability Partnerships Act 2005 and section 28 of the Limited Partnerships Act 2008. 2-2 Examples of natural persons with executive authority in a company include the Chairman and Chief Executive Officer. An example of a natural person with executive authority in a partnership is the Managing Partner. Customer 2-3 When performing Customer Due Diligence ('CDD') measures in the scenarios below, the following approaches may be adopted: (a) Portfolio Managers A CMI (for e.g. a securities broker or fund management company) may encounter cases where the customer is the primary manager of a fund (as set out in Scenario 1 below). In thi

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.16

> A CMI shall not be required to inquire if there exists any beneficial owner in relation to a customer that is - (a) an entity listed and traded on the Singapore Exchange; (b) an entity listed on a stock exchange outside of Singapore that is subject to - (i) regulatory disclosure requirements; and (ii) requirements relating to adequate transparency in respect of its beneficial owners (imposed through stock exchange rules, law or other enforceable means); (c) a financial institution set out in Appendix 1; (d) a financial institution incorporated or established outside Singapore that is subject to and supervised for compliance with AML/CFT requirements consistent with standards set by the FATF; or (e) an investment vehicle where the managers are financial institutions 6 - (i) set out in Appendix 1; or (ii) incorporated or established outside Singapore but are subject to and supervised for c

---

## gs-0064 · multi_hop · confidence 1.0

**Q.** When a trust company identifies an effective controller of a trust relevant party that is a legal arrangement, what specific information must it obtain to verify that person's identity?

**A.** The trust company must obtain the full name and any aliases, a unique identification number such as an identity card or passport number, the residential address, the date of birth, and the nationality of the identified effective controller.

**Gold span** — Guidelines to Notice TCA-N03 on Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 6

> Notice Paragraph 6.2 6-1 Where There Are Reasonable Grounds for Suspicion prior to the Establishment of Business Contact 6-1-1 In arriving at its decision for each case, a trust company should take into account the relevant facts, including information that may be made available by the authorities and conduct a proper risk assessment. Notice Paragraphs 6.4 to 6.18 6-2 CDD Measures under Paragraphs 6.4 to 6.18 6-2-1 Paragraph 6.4(a) of the Notice provides that where the legal arrangement is constituted before the establishment of business contact, the trust company shall identify the trust relevant party before the provision of any trust business services. Examples of such instances are where a trustee retires and a new trust company is appointed in its place or where an existing trustee appoints a trust company for trust administration services. 6-2-2 When relying on documents, a trust c

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 6.14

> Where there is one or more effective controllers in relation to a trust relevant party, the trust company shall identify the effective controllers before the trust is constituted (provided that where the settlor has constituted the trust before establishing business contact with the trust company, the trust company shall identify the effective controllers before the provision of any trust business services). For the purposes of identifying the effective controllers, the trust company shall - (a) for trust relevant parties that are legal persons - (i) identify the natural persons (whether acting alone or together) who ultimately own the trust relevant party; (ii) to the extent that there is doubt under subparagraph (i) as to whether the natural persons who ultimately own the trust relevant party are the effective controllers or where no natural persons ultimately own the trust relevant pa

---

## gs-0066 · multi_hop · confidence 1.0

**Q.** If a Credit Card Licensee acquires another institution's business along with its customer records without any concerns about their accuracy, what additional verification steps regarding due diligence are required before relying on those existing AML/CFT measures?

**A.** The acquiring licensee must have conducted due diligence enquiries that raised no doubts regarding the adequacy of the previously adopted AML/CFT measures and documented these enquiries to satisfy the exception conditions.

**Gold span** — Guidelines to Notice 626A on Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 6

> Notice Paragraph 6.2 6-1 Where There Are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations 6-1-1 In arriving at its decision for each case, a licensee should take into account the relevant facts, including information that may be made available by the authorities and conduct a proper risk assessment. Notice Paragraphs 6.4 to 6.17 6-2 CDD Measures under Paragraphs 6.4 to 6.17 6-2-1 When relying on documents, a licensee should be aware that the best documents to use to verify the identity of the customer are those most difficult to obtain illicitly or to counterfeit. These may include government-issued identity cards or passports, reports from independent company registries, published or audited annual reports and other reliable sources of information. The rigour of the verification process should be commensurate with the customer's risk profile. 6-2-2 A lic

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 6.29

> When a licensee ('acquiring licensee ') acquires, either in whole or in part, the business of another financial institution (whether in Singapore or elsewhere), the acquiring licensee shall perform the measures as required by paragraphs 6, 7 and 8, on the customers acquired with the business at the time of acquisition except where the acquiring licensee has ⎯ (a) acquired at the same time all corresponding customer records (including CDD information) and has no doubt or concerns about the veracity or adequacy of the information so acquired; and (b) conducted due diligence enquiries that have not raised any doubt on the part of the acquiring licensee as to the adequacy of AML/CFT measures previously adopted in relation to the business or part thereof now acquired by the acquiring licensee, and document such enquiries. Timing for Verification

---

## gs-0067 · multi_hop · confidence 1.0

**Q.** When an approved trustee acquires a financial business along with its customer records without raising any concerns about their accuracy or previous anti-money laundering measures, what specific verification actions are they exempt from performing on those acquired customers?

**A.** The acquiring approved trustee is exempt from performing the identity verification and due diligence measures required for those customers because they have simultaneously acquired all corresponding records with no doubts about their veracity and have conducted sufficient enquiries confirming the adequacy of the previous measures.

**Gold span** — Guidelines to Notice SFA 13-N01 on Prevention of Money Laundering and Countering the Financing of Terrorism - Approved Trustees · clause 6

> Notice Paragraph 6.2 6-1 Where There Are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations 6-1-1 In arriving at its decision for each case, an approved trustee should take into account the relevant facts, including information that may be made available by the authorities and conduct a proper risk assessment. Notice Paragraphs 6.4 to 6.17 6-2 CDD Measures Under Paragraphs 6.4 to 6.17 6-2-1 When relying on documents, an approved trustee should be aware that the best documents to use to verify the identity of the customer are those most difficult to obtain illicitly or to counterfeit. These may include government issued identity cards or passports, reports from independent company registries, published or audited annual reports and other reliable sources of information. The rigour of the verification process should be commensurate with the customer's risk pr

**Gold span** — Notice SFA 13-N01 to Approved Trustees on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.30

> When an approved trustee ('acquiring approved trustee') acquires, either in whole or in part, the business of another financial institution (whether in Singapore or elsewhere), the acquiring approved trustee shall perform the measures as required by paragraphs 6, 7 and 8, on the customers acquired with the business at the time of acquisition except where the acquiring approved trustee has ⎯ (a) acquired at the same time all corresponding customer records (including CDD information) and has no doubt or concerns about the veracity or adequacy of the information so acquired; and (b) conducted due diligence enquiries that have not raised any doubt on the part of the acquiring approved trustee as to the adequacy of AML/CFT measures previously adopted in relation to the business or part thereof now acquired by the acquiring approved trustee, and document such enquiries. Where Measures are Not

---

## gs-0068 · multi_hop · confidence 1.0

**Q.** What specific types of suspicious activity information must a Singapore-based finance company share with its group-level compliance functions, provided it has adequate safeguards to protect confidentiality?

**A.** The institution is required to share positive name matches from screening against ML/TF sources, lists of customers exited due to suspicion, and names of parties on whom suspicious transaction reports were filed.

**Gold span** — Guidelines to MAS Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism - Finance Companies · clause 15

> 15-1 As internal policies and procedures serve to guide employees and officers in ensuring compliance with AML/CFT laws and regulations, it is important that a finance company updates its policies and procedures in a timely manner, to take into account new operational, legal and regulatory developments and emerging or new ML/TF risks. Notice Paragraphs 15.3 to 15.9 15-2 Group Policy 15-2-1 For the avoidance of doubt, Singapore branches of finance companies incorporated outside Singapore need not comply with paragraphs 15.3 to 15.9 of the Notice. Paragraphs 15.3 to 15.9 of the Notice are intended to be applied by a finance company incorporated in Singapore to its branches and subsidiaries, but not to its parent entity and the finance company's other related corporations. 15-2-2 In relation to paragraph 15.6 of the Notice, examples of the types of information that should be shared within t

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 15.6

> Subject to the finance company putting in place adequate safeguards to protect the confidentiality and use of any information that is shared, the finance company shall develop and implement group policies and procedures for its branches and subsidiaries within the financial group, to share information required for the purposes of CDD and for money laundering and terrorism financing risk management, to the extent permitted by the law of the countries or jurisdictions that its branches and subsidiaries are in.

---

## gs-0069 · multi_hop · confidence 1.0

**Q.** When new risk information arrives that indicates a customer lacks current details or key individuals are unknown, what specific internal review must a Financial Institution's Information Platform participant undertake regarding their existing customer data?

**A.** The institution must conduct a review of its current CDD records and supporting documents for the relevant party or key individuals. This action is necessary to ensure the information remains relevant and up-to-date, especially when gaps are identified.

**Gold span** — Guidelines to MAS Notice FSM-N02 on Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions’ Information Sharing Platform · clause 4

> Responsibility of the requester 4-1 For effective management and mitigation of ML/TF/PF Risk, a prescribed financial institution should put in place systems and processes to ensure that, upon receipt of risk information received as part of a Response, officers who are tasked with undertaking an assessment (i) have timely access to the risk information received, and (ii) are adequately trained on the proper use of platform information for customer risk assessments. 4-2 A prescribed financial institution should undertake the risk assessment mentioned in paragraph 4.1(a) of the Notice in a timely manner. 4-3 The results of the risk assessment must be properly documented and should be approved by an appropriately senior and/or qualified compliance officer of the prescribed financial institution. 4-4 A prescribed financial institution is also reminded to ensure that it complies with its AML/C

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 6.24

> A bank shall ensure that the CDD data, documents and information obtained in respect of customers, natural persons appointed to act on behalf of the customers, connected parties of the customers and beneficial owners of the customers, are relevant and kept up-to-date by undertaking reviews of existing CDD data, documents and information, particularly for higher risk categories of customers.

---

## gs-0070 · multi_hop · confidence 1.0

**Q.** What specific internal policies must a finance company develop to allow establishing business relations before completing identity verification for natural persons acting on behalf of a customer?

**A.** A finance company must develop and implement internal risk management policies that define the conditions under which it can establish business relations with natural persons appointed to act on behalf of a customer prior to verifying their identity, while also ensuring such verification is completed as soon as reasonably practicable.

**Gold span** — Guidelines to MAS Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism - Finance Companies · clause 6

> Notice Paragraph 6.2 6-1 Where There Are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations or Undertaking any Transaction without opening an Account 6-1-1 In arriving at its decision for each case, a finance company should take into account the relevant facts, including information that may be made available by the authorities and conduct a proper risk assessment. Notice Paragraphs 6.3 to 6.4 6-2 When CDD is to be Performed and Linked Transactions 6-2-1 Paragraph 6.4 of the Notice is applicable to a finance company when it undertakes transactions for customers who or which have not established business relations with the finance company. 6-2-2 A finance company should monitor whether the related or linked transactions exceed the thresholds set out in paragraph 6.3(b) or paragraph 6.3(d) of the Notice and should take these into consideration when formulatin

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 6.34

> Where the finance company establishes business relations with a customer before verifying the identity of the customer as required by paragraph 6.9, natural persons appointed to act on behalf of the customer as required by paragraph 6.10(b), and beneficial owners of the customer as required by paragraph 6.14B, the finance company shall - (a) develop and implement internal risk management policies and procedures concerning the conditions under which such business relations may be established prior to verification; and (b) complete such verification as soon as is reasonably practicable. Where Measures are Not Completed

---

## gs-0072 · multi_hop · confidence 1.0

**Q.** If an Approved Exchange or Recognised Market Operator establishes a business relationship with a customer before verifying their identity, what specific internal requirements must they implement and how should they proceed with completing that verification?

**A.** They must develop and implement internal risk management policies outlining the conditions under which such early establishment is permitted, and they must complete the verification as soon as reasonably practicable.

**Gold span** — Guidelines to Notice SFA02-N05 on Prevention of Money Laundering and Countering the Financing of Terrorism - Approved Exchanges and Recognised Market Operators · clause 6

> Notice Paragraph 6.2 6-1 Where There Are Reasonable Grounds for Suspicion prior to the Establishment of Business Relations or Undertaking any Transaction without opening an Account 6-1-1 In arriving at its decision for each case, an AE or RMO should take into account the relevant facts, including information that may be made available by the authorities and conduct a proper risk assessment. Notice Paragraphs 6.3 to 6.4 6-2 When CDD is to be Performed and Linked Transactions 6-2-1 Paragraph 6.4 of the Notice is applicable to an AE or RMO when it undertakes transactions for customers who or which have not established business relations with the AE or RMO. 6-2-2 An AE or RMO should monitor whether the related or linked transactions exceed the threshold set out in paragraph 6.3(b) of the Notice and should take these into consideration when formulating scenarios and parameters. 6-2-3 Two or m

**Gold span** — Notice SFA02-N05 to Approved Exchanges and Recognised Market Operators on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.40

> If the AE or RMO establishes business relations with a customer before verifying the identity of the customer as required by paragraph 6.11, natural persons appointed to act on behalf of the customer as required by paragraph 6.12(b), and beneficial owners of the customer as required by paragraph 6.19B, the AE or RMO must - (a) develop and implement internal risk management policies and procedures concerning the conditions under which the business relations may be established before verification; and (b) complete the verification as soon as is reasonably practicable. [MAS Notice SFA02-N05 (Amendment) 2025] If Measures are Not Completed

---

## gs-0073 · multi_hop · confidence 1.0

**Q.** For a merchant bank that identifies a customer as a politically exposed person, what specific enhanced due diligence steps must be taken beyond standard checks, and which additional high-risk customer categories generally trigger similar enhanced measures?

**A.** The bank must obtain senior management approval before establishing business relations or conducting transactions, establish the source of wealth and funds, and conduct enhanced monitoring. Additionally, if the customer belongs to other high-risk categories such as those from higher-risk jurisdictions, involved in cash-intensive activities, or exhibiting signs of shell company misuse, these same enhanced measures should also be applied.

**Gold span** — Guidelines to MAS Notice 1014 on Prevention of Money Laundering and Countering the Financing of Terrorism - Merchant Banks · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, a merchant bank shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.7 of the Notice include - (a) Customer risk (i) customers from higher risk businesses / activities / sectors identified in Singapore's NRA, as well as other higher risk businesses / activities / sectors identified by the merchant bank; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relation is conducted under unusual circumstances (e.g. significant unexplained geographic distance between the merchant bank and the customer); (v) companies that have

**Gold span** — Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks · clause 8.3

> A merchant bank shall, in addition to performing CDD measures (specified in paragraph 6), perform at least the following enhanced CDD measures where a customer or any beneficial owner of the customer is determined by the merchant bank to be a politically exposed person, or a family member or close associate of a politically exposed person under paragraph 8.2: (a) obtain approval from the merchant bank's senior management to establish or continue business relations with, or undertake any transaction without an account being opened for the customer; (b) establish, by appropriate and reasonable means, the source of wealth and source of funds of the customer and any beneficial owner of the customer; and (c) conduct, during the course of business relations with the customer, enhanced monitoring of business relations with the customer. In particular, the merchant bank shall increase the degree

---

## gs-0074 · multi_hop · confidence 1.0

**Q.** For a Digital Payment Token Service, which specific customer risk factors involving ownership structure or business relations require Enhanced CDD measures?

**A.** A Digital Payment Token Service must perform enhanced CDD if the customer's ownership structure appears unusually complex, involves personal asset holding vehicles or nominee shareholders, or if business relations occur without an account under unusual circumstances such as significant geographic distance.

**Gold span** — Guidelines to Notice PSN02 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Payment Token Service · clause 8

> 8-1 Where the ML/TF risks are identified to be higher, a payment service provider shall take enhanced CDD ('ECDD') measures to mitigate and manage those risks. 8-2 Examples of potentially higher risk categories under paragraph 8.7 of the Notice include - (a) Customer risk (i) customers from higher risk businesses/ activities/ sectors identified in Singapore's NRA, guidance from the Authority, as well as other higher risk businesses/ activities/ sectors identified by the payment service provider; (ii) the ownership structure of the legal person or arrangement appears unusual or excessively complex given the nature of the legal person's or legal arrangement's business; (iii) legal persons or legal arrangements that are personal asset holding vehicles; (iv) the business relations with a customer or transactions undertaken without an account being opened that are conducted under unusual circ

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 8.4

> A payment service provider may adopt a risk-based approach in determining whether to perform enhanced CDD measures or the extent of enhanced CDD measures to be performed for ⎯ (a) domestic politically exposed persons, their family members and close associates; (b) international organisation politically exposed persons, their family members and close associates; or (c) politically exposed persons who have stepped down from their prominent public functions, taking into consideration the level of influence such persons may continue to exercise after stepping down from their prominent public functions, their family members and close associates, except in cases where their business relations with the payment service provider or transaction without an account being opened by the payment service provider present a higher risk for money laundering or terrorism financing. Other Higher Risk Catego

---

## gs-0077 · comparative · confidence 1.0

**Q.** How does the obligation for beneficiary institutions to monitor wire transfers lacking required originator or beneficiary information apply across Banks, Merchant Banks, and Finance Companies?

**A.** The requirement is identical for all three institution types: each must take reasonable measures, such as post-event or real-time monitoring where feasible, to detect cross-border wire transfers missing the necessary originator or beneficiary details.

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 11.10

> A bank that is a beneficiary institution shall take reasonable measures, including postevent monitoring or real-time monitoring where feasible, to identify cross-border wire transfers that lack the required wire transfer originator or required wire transfer beneficiary information.

**Gold span** — Notice 1014 Prevention of Money Laundering and Countering the Financing of Terrorism – Merchant Banks · clause 11.10

> A merchant bank that is a beneficiary institution shall take reasonable measures, including post-event monitoring or real-time monitoring where feasible, to identify crossborder wire transfers that lack the required wire transfer originator or required wire transfer beneficiary information.

**Gold span** — Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies · clause 11.10

> A finance company that is a beneficiary institution shall take reasonable measures, including post-event monitoring or real-time monitoring where feasible, to identify crossborder wire transfers that lack the required wire transfer originator or required wire transfer beneficiary information.

---

## gs-0078 · comparative · confidence 1.0

**Q.** How does the definition of 'business relations' differ among Specified Payment Services, Trust Companies, and Banks, and which institution types explicitly include providing financial advice as part of that definition?

**A.** The requirement is different for Banks compared to the other two institution types. For Specified Payment Services, business relations are defined strictly as opening or maintaining an account. For Trust Companies, the provided text defines business contact but does not define 'business relations.' However, for Banks, the definition explicitly includes both opening or maintaining an account and providing financial advice.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 2.1

> For the purposes of this Notice ⎯ 'AML/CFT' means anti -money laundering 1 and countering the financing of terrorism; 'Authority' means the Monetary Authority of Singapore; 'bank' has the same meaning as in section 2(1) of the Banking Act 1970; 'bank in Singapore' has the same meaning as in section 2(1) of the Banking Act 1970; 'bearer negotiable instrument' means ⎯ (a) a traveller's cheque; or (b) any negotiable instrument that is in bearer form, indorsed without any restriction, made out to a fictitious payee or otherwise in such form that title thereto passes upon delivery, and includes a negotiable instrument that has been signed but with the payee's name omitted; 1 In this Notice, money laundering includes proliferation financing, and all references in this Notice to money laundering (including money laundering risks) shall be construed accordingly. 'beneficial owner', in relation t

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 2.1

> For the purposes of this Notice - 'AML/CFT' means anti -money laundering 1 and countering the financing of terrorism; 'Authority' means the Monetary Authority of Singapore; 'business contact' means any contact (including the undertaking of any transactions) between the trust company and the trust relevant party in the course of the provision of trust business services by the trust company; 'CDD measures' or 'customer due diligence measures' means the measures required by paragraph 6; 'CDSA' means the Corruption, Drug Trafficking and Other Serious Crimes (Confiscation of Benefits) Act 1992; 'connected party' - (a) in relation to a legal person (other than a partnership), means any director or any natural person having executive authority in the legal person; 1 In this Notice, money laundering includes proliferation financing, and all references in this Notice to money laundering (includin

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 2.1

> For the purposes of this Notice - 'AML/CFT' means anti -money laundering 1 and countering the financing of terrorism; 'Authority' means the Monetary Authority of Singapore; 'bank' means a bank in Singapore, as defined in section 2 of the BA; 'beneficial owner', in relation to a customer of a bank, means the natural person who ultimately owns or controls the customer or the natural person on whose behalf a transaction is conducted or business relations are established, and includes any person who exercises ultimate effective control over a legal person or legal arrangement; 'beneficiary institution' means - 1 In this Notice, money laundering includes proliferation financing, and all references in this Notice to money laundering (including money laundering risks) shall be construed accordingly. [MAS Notice 626 (Amendment) 2025] (a) in relation to a wire transfer, the financial institution

---

## gs-0080 · comparative · confidence 1.0

**Q.** When an acquiring entity takes over part of another institution's business without transferring all records, does the specific type of license—Trust Company, Bank, or Capital Markets Intermediary—affect what due diligence steps must be performed on the acquired customers?

**A.** The requirement is identical for Trust Companies, Banks, and Capital Markets Intermediaries; each must perform measures 6, 7, and 8 unless they simultaneously received all records with no concerns and completed satisfactory due diligence inquiries.

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 6.30

> When a trust company ('acquiring trust company') acquires, either in whole or in part, the business of another financial institution (whether in Singapore or elsewhere), the acquiring trust company shall perform the measures as required by paragraphs 6, 7 and 8, on the trust relevant parties acquired with the business at the time of acquisition except where the acquiring trust company has - (a) acquired at the same time all corresponding records of the trust relevant parties (including CDD information) and has no doubt or concerns about the veracity or adequacy of the information so acquired; and (b) conducted due diligence enquiries that have not raised any doubt on the part of the acquiring trust company as to the adequacy of AML/CFT measures previously adopted in relation to the business or part thereof now acquired by the acquiring trust company, and document such enquiries. Where Me

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 6.30

> When a bank ('acquiring bank') acquires, either in whole or in part, the business of another financial institution (whether in Singapore or elsewhere), the acquiring bank shall perform the measures as required by paragraphs 6, 7 and 8, on the customers acquired with the business at the time of acquisition except where the acquiring bank has - (a) acquired at the same time all corresponding customer records (including CDD information) and has no doubt or concerns about the veracity or adequacy of the information so acquired; and (b) conducted due diligence enquiries that have not raised any doubt on the part of the acquiring bank as to the adequacy of AML/CFT measures previously adopted in relation to the business or part thereof now acquired by the acquiring bank and document such enquiries. CDD Measures for Non-Account Holder

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.30

> When a CMI ('acquiring CMI') acquires, either in whole or in part, the business of another financial institution (whether in Singapore or elsewhere), the acquiring CMI shall perform the measures as required by paragraphs 6, 7 and 8, on the customers acquired with the business at the time of acquisition except where the acquiring CMI has - (a) acquired at the same time all corresponding customer records (including CDD information) and has no doubt or concerns about the veracity or adequacy of the information so acquired; and (b) conducted due diligence enquiries that have not raised any doubt on the part of the acquiring CMI as to the adequacy of AML/CFT measures previously adopted in relation to the business or part thereof now acquired by the acquiring CMI and document such enquiries. Measures for Non-Account Holder

---

## gs-0081 · comparative · confidence 1.0

**Q.** How do the identification obligations for legal person customers differ between Specified Payment Services and Variable Capital Companies (VCCs), specifically regarding the collection of unique identification numbers versus proof of legal existence?

**A.** For Specified Payment Services, providers must obtain a unique identification number for connected parties unless risks are low and such data is unobtainable, whereas VCCs are required to verify the customer's legal form, proof of existence, constitution, and powers using reliable independent sources.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 7.8

> Where the customer is a legal person or legal arrangement, the payment service provider shall identify the connected parties of the customer, by obtaining at least the following information of each connected party: (a) full name, including any aliases; and (b) unique identification number (such as an identity card number, birth certificate number or passport number of the connected party). 7.8A Where the payment service provider - (a) has assessed that the money laundering and terrorism financing risks in relation to the customer are not high; and (b) is unable to obtain the unique identification number of the connected party after taking reasonable measures,

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 7.8

> A VCC shall verify the identity of the customer using reliable, independent source data, documents or information. Where the customer is a legal person or legal arrangement, a VCC shall verify the legal form, proof of existence, constitution and powers that regulate and bind the customer, using reliable, independent source data, documents or information. (III) Identification and Verification of Identity of Natural Person Appointed to Act on a Customer's Behalf

---

## gs-0082 · comparative · confidence 1.0

**Q.** How do the risk assessment obligations for Trust Companies, Banks, and Capital Markets Intermediaries differ when dealing with customers from jurisdictions under FATF countermeasures versus those with inadequate AML/CFT measures versus shell entities?

**A.** The requirement is the same for all three institution types: they must treat business relations as higher risk for customers from jurisdictions under FATF countermeasures, but only assess risk for those from jurisdictions with inadequate AML/CFT measures or shell entities.

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 8.6

> For the purposes of paragraph 8.5, circumstances where a trust relevant party presents or may present a higher risk for money laundering or terrorism financing include but are not limited to the following: (a) where a trust relevant party, or any effective controller of the trust relevant party is from or in a country or jurisdiction in relation to which the FATF has called for countermeasures, the trust company shall treat any business contact with such trust relevant party as presenting a higher risk for money laundering or terrorism financing; (b) where a trust relevant party, or any effective controller of the trust relevant party is from or in a country or jurisdiction known to have inadequate AML/CFT measures, as determined by the trust company for itself, or notified to trust companies generally by the Authority or other foreign regulatory authorities, the trust company shall asse

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 8.6

> For the purposes of paragraph 8.5, circumstances where a customer presents or may present a higher risk for money laundering or terrorism financing include but are not limited to the following: (a) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction in relation to which the FATF has called for countermeasures, the bank shall treat any business relations with or transactions for any such customer as presenting a higher risk for money laundering or terrorism financing; (b) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction known to have inadequate AML/CFT measures, as determined by the bank for itself, or notified to banks generally by the Authority or other foreign regulatory authorities, the bank shall assess whether any such customer presents a higher risk for money laundering or terrorism financi

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 8.6

> For the purposes of paragraph 8.5, circumstances where a customer presents or may present a higher risk for money laundering or terrorism financing include but are not limited to the following: (a) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction in relation to which the FATF has called for countermeasures, the CMI shall treat any business relations with or transactions for any such customer as presenting a higher risk for money laundering or terrorism financing; (b) where a customer or any beneficial owner of the customer is from or in a country or jurisdiction known to have inadequate AML/CFT measures, as determined by the CMI for itself, or notified to CMIs generally by the Authority or other foreign regulatory authorities, the CMI shall assess whether any such customer presents a higher risk for money laundering or terrorism financing;

---

## gs-0083 · comparative · confidence 1.0

**Q.** How do the requirements for documentation, risk assessment timing, and mitigation mechanisms differ between Specified Payment Services, Trust Companies, and Banks regarding new products, practices, or technologies?

**A.** Specified Payment Services must document their risk assessments, keep them up-to-date, and provide information to the Authority, whereas Trust Companies and Banks are only required to undertake risk assessments before launch and take appropriate mitigation measures without a specific mandate for documentation or regulatory reporting in this context.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 5.2

> The appropriate steps referred to in paragraph 5.1 shall include ⎯ (a) documenting the payment service provider 's risk assessments; (b) considering all the relevant risk factors before determining the level of overall risk and the appropriate type and extent of mitigation to be applied; (c) keeping the payment service provider 's risk assessments up-to-date; and (d) having appropriate mechanisms to provide its risk assessment information to the Authority. Risk Mitigation

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 5.2

> A trust company shall undertake the risk assessments, prior to the launch or use of such products, practices and technologies (to the extent such use is permitted by this Notice), and shall take appropriate measures to manage and mitigate the risks.

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 5.2

> A bank shall undertake the risk assessments, prior to the launch or use of such products, practices and technologies (to the extent such use is permitted by this Notice) and shall take appropriate measures to manage and mitigate the risks.

---

## gs-0085 · comparative · confidence 1.0

**Q.** How do the risk mitigation documentation steps for Trust Companies, Banks, and Capital Markets Intermediaries compare to one another?

**A.** The requirements are identical for all three institution types, each mandating that they document their risk assessments, evaluate relevant factors to determine overall risk levels and mitigation measures, keep these assessments current, and establish mechanisms to share this information with the Authority.

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 4.2

> The appropriate steps referred to in paragraph 4.1 shall include - (a) documenting the trust company's risk assessments; (b) considering all the relevant risk factors before determining the level of overall risk and the appropriate type and extent of mitigation to be applied; (c) keeping the trust company's risk assessments up -to-date; and (d) having appropriate mechanisms to provide its risk assessment information to the Authority. Risk Mitigation

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 4.2

> The appropriate steps referred to in paragraph 4.1 shall include - (a) documenting the bank's risk assessments; (b) considering all the relevant risk factors before determining the level of overall risk and the appropriate type and extent of mitigation to be applied; (c) keeping the bank's risk assessments up -to-date; and (d) having appropriate mechanisms to provide its risk assessment information to the Authority. Risk Mitigation

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 4.2

> The appropriate steps referred to in paragraph 4.1 shall include - (a) documenting the CMI's risk assessments; (b) considering all the relevant risk factors before determining the level of overall risk and the appropriate type and extent of mitigation to be applied; (c) keeping the CMI's risk assessments up -to-date; and (d) having appropriate mechanisms to provide its risk assessment information to the Authority. Risk Mitigation

---

## gs-0088 · comparative · confidence 1.0

**Q.** For both Digital Payment Token Service providers and Credit Card or Charge Card Licensees acting as intermediary institutions, do they share the same obligation to pass along transfer details?

**A.** Yes, the requirement is identical for both institution types: when an intermediary effects a value transfer, it must immediately and securely transmit the accompanying information to the recipient institution.

**Gold span** — Notice PSN02 Prevention of Money Laundering and Countering the Financing of Terrorism – Digital Payment Token Service · clause 13.17

> Where a payment service provider that is an intermediary institution effects a value transfer to another intermediary institution or a beneficiary institution, the payment service provider shall immediately and securely provide the information accompanying the value transfer, to that other intermediary institution or beneficiary institution.

**Gold span** — Notice 626A Prevention of Money Laundering and Countering the Financing of Terrorism – Credit Card or Charge Card Licensees · clause 13.17

> Where a licensee that is an intermediary institution effects a value transfer to another intermediary institution or a beneficiary institution, the licensee shall immediately and securely provide the information accompanying the value transfer, to that other intermediary institution or beneficiary institution.

---

## gs-0089 · comparative · confidence 1.0

**Q.** How do the AML/CFT rules for overseas branches compare across Capital Markets Intermediaries, Financial Institutions Dealing In Precious Stones And Precious Metals, and Variable Capital Companies regarding conflicting host country standards?

**A.** The requirement is identical for all three institution types: each must instruct its overseas branch or subsidiary to apply the higher standard between Singapore and the host jurisdiction, provided that local law allows it.

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 14.8

> Where the AML/CFT requirements in the host country or jurisdiction differ from those in Singapore, the CMI shall require that the overseas branch or subsidiary apply the higher of the two standards, to the extent that the law of the host country or jurisdiction so permits.

**Gold span** — Notice PSM-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Financial Institutions Dealing In Precious Stones And Precious Metals · clause 14.8

> Where the AML/CFT requirements in the host country or jurisdiction differ from those in Singapore, the financial institution shall require that the overseas branch or subsidiary apply the higher of the two standards, to the extent that the law of the host country or jurisdiction so permits.

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 14.8

> Where the AML/CFT requirements in the host country or jurisdiction differ from those in 7 Subject to section 57of the CDSA on tipping-off, information shared may include an STR, the underlying information of the STR, or the fact that an STR was filed. [MAS Notice VCC-N01 (Amendment) 2022] Singapore, the VCC shall require that the overseas branch or subsidiary apply the higher of the two standards, to the extent that the law of the host country or jurisdiction so permits.

---

## gs-0090 · comparative · confidence 1.0

**Q.** How do the Politically Exposed Person (PEP) screening obligations for Trust Companies differ from those applicable to Banks and Capital Markets Intermediaries?

**A.** The core obligation for all three institution types is identical: each must implement internal systems to screen customers, their representatives, connected parties, and beneficial owners for PEP status or family/associate ties. However, the requirement applies to different subjects depending on the institution; it covers trust relevant parties for Trust Companies, whereas it covers customers for both Banks and Capital Markets Intermediaries. Additionally, Banks have a specific extra instruction to integrate information received through COSMIC into their existing screening frameworks.

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 8.2

> A trust company shall implement appropriate internal risk management systems, policies, procedures and controls to determine if a trust relevant party, any natural person appointed to act on behalf of the trust relevant party, any connected party of the trust relevant party, or any effective controller of the trust relevant party is a politically exposed person, or a family member or close associate of a politically exposed person.

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 8.2

> A bank shall implement appropriate internal risk management systems, policies, procedures and controls to determine if a customer, any natural person appointed to act on behalf of the customer, any connected party of the customer or any beneficial owner of the customer is a politically exposed person, or a family member or close associate of a politically exposed person. If a bank is participating in COSMIC, the bank must ensure that under its internal risk management systems, policies, procedures and controls in this paragraph 8.2, the bank takes into account information relating to the aforementioned persons that it has received through COSMIC.

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 8.2

> A CMI shall implement appropriate internal risk management systems, policies, procedures and controls to determine if a customer, any natural person appointed to act on behalf of the customer, any connected party of the customer or any beneficial owner of the customer is a politically exposed person, or a family member or close associate of a politically exposed person.

---

## gs-0091 · comparative · confidence 1.0

**Q.** How does the obligation to keep Customer Due Diligence data relevant and up-to-date differ among Trust Companies, Banks, and Capital Markets Intermediaries?

**A.** The core obligation is identical for all three institution types: they must review existing CDD data particularly for higher risk categories. The difference lies in the specific subjects covered; Trust Companies must include legal arrangements and trust relevant parties, whereas Banks and Capital Markets Intermediaries focus on customers and their beneficial owners.

**Gold span** — Notice TCA-N03 Prevention of Money Laundering and Countering the Financing of Terrorism - Trust Companies · clause 6.24

> A trust company shall ensure that CDD data, documents and information obtained in respect of the legal arrangement, trust relevant parties, natural persons appointed to act on behalf of the trust relevant parties, connected parties of the trust relevant parties, effective controllers of a trust relevant party, are relevant and kept up-to-date by undertaking reviews of existing CDD data, documents and information, particularly for higher risk categories of trust relevant parties.

**Gold span** — Notice 626 Prevention of Money Laundering and Countering the Financing of Terrorism – Banks · clause 6.24

> A bank shall ensure that the CDD data, documents and information obtained in respect of customers, natural persons appointed to act on behalf of the customers, connected parties of the customers and beneficial owners of the customers, are relevant and kept up-to-date by undertaking reviews of existing CDD data, documents and information, particularly for higher risk categories of customers.

**Gold span** — Notice SFA 04-N02 to Capital Markets Intermediaries on Prevention of Money Laundering and Countering the Financing of Terrorism · clause 6.24

> A CMI shall ensure that the CDD data, documents and information obtained in respect of customers, natural persons appointed to act on behalf of the customers, connected parties of the customers and beneficial owners of the customers, are relevant and kept up-to-date by undertaking reviews of existing CDD data, documents and information, particularly for higher risk categories of customers.

---

## gs-0092 · comparative · confidence 1.0

**Q.** How does the obligation for Specified Payment Services and Variable Capital Companies to inquire into transaction backgrounds differ?

**A.** The requirement is identical for both Specified Payment Services and Variable Capital Companies, as each must inquire into the background and purpose of the relevant transactions to the extent possible and document their findings for potential disclosure to authorities.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 7.30

> A payment service provider shall, to the extent possible, inquire into the background and purpose of the transactions in paragraph 7.28 and document its findings with a view to making this information available to the relevant authorities should the need arise.

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 7.30

> A VCC shall, to the extent possible, inquire into the background and purpose of the transactions in paragraph 7.28 and document its findings with a view to making this information available to the relevant authorities should the need arise.

---

## gs-0094 · comparative · confidence 1.0

**Q.** For both Specified Payment Services and Variable Capital Companies, how does the requirement to handle a customer suspected of drug dealing or terrorism financing differ before establishing business relations?

**A.** The requirement is the same for both institution types: each must refuse to establish business relations or undertake the transaction and file an STR 4 if they have reasonable grounds to suspect the funds are proceeds of crime or related to terrorism financing.

**Gold span** — Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services · clause 7.2

> Prior to a payment service provider establishing business relations or undertaking any transaction without opening an account, where the payment service provider has any reasonable grounds to suspect that the assets or funds of a customer are proceeds of drug dealing or criminal conduct as defined in the CDSA, or are property related to the facilitation or carrying out of any terrorism financing offence as defined in the TSOFA, the payment service provider shall ⎯ (a) not establish business relations with, or undertake a transaction for, the customer; and (b) file an STR 4 , and extend a copy to the Authority upon request. [MAS Notice PSN01 (Amendment) 2025] When CDD is to be Performed

**Gold span** — Notice VCC-N01 Prevention of Money Laundering and Countering the Financing of Terrorism – Variable Capital Companies (VCCs) · clause 7.2

> Prior to a VCC establishing business relations with a customer, where the VCC has any reasonable grounds to suspect that the assets or funds of a customer are proceeds of drug dealing or criminal conduct as defined in the CDSA, or are property related to the facilitation or carrying out of any terrorism financing offence as defined in the TSOFA, the VCC shall ⎯ (a) not establish business relations with, or undertake a transaction for, the customer; and (b) file an STR 4 , and extend a copy to the Authority upon request. [MAS Notice VCC-N01 (Amendment) 2025] When CDD is to be Performed

---

## gs-0101 · temporal · confidence 1.0

**Q.** When did the amendment regarding submission requirements take effect?

**A.** The updated submission requirements became effective on 16 March 2021.

**Gold span** — Notice 129 on Insurance Returns (Accounts and Statements) · clause 4

> MAS Notice 129 (Amendment) 2021 dated 15 March 2021 with effect from 16 March 2021. Appendix A SUBMISSION, SIGNATORY AND AUDIT REQUIREMENTS SUBMISSION REQUIREMENTS Appendix A - 1 SUBMISSION REQUIREMENTS Appendix A - 2 SUBMISSION REQUIREMENTS Appendix A - 3 SUBMISSION REQUIREMENTS Appendix A - 4 SUBMISSION REQUIREMENTS Appendix A - 5 SUBMISSION REQUIREMENTS Appendix A - 6 Appendix B LIST OF INSURANCE FORMS FOR MAINSTREAM INSURERS Co Code Year Month NAME OF INSURER _____________________________________________________________________________________________________ FORM A1 - STATEMENT OF FINANCIAL POSITION AS AT _____________________ MARKET VALUE ANNEX A1-1 OTHER INVESTMENTS AS AT _____________________ NOTIONAL PRINCIPAL AMOUNT ANNEX A1-2 OUTSTANDING PREMIUMS AS AT _____________________ ANNEX A1-3 REINSURANCE RECOVERABLES ON PAID CLAIMS AS AT _____________________ ANNEX A1-4 OTHER ASSETS A

---

## gs-0102 · temporal · confidence 1.0

**Q.** When did the requirements for outstanding S$ credit facilities become effective?

**A.** The regulations regarding outstanding S$ credit facilities became effective on 1 July 2021.

**Gold span** — Notice SFA 04-N04 Lending of Singapore Dollar to Non-Resident Financial Institutions for Holders of Capital Markets Services Licence · clause 2

> MAS Notice SFA 04-N04 (Amendment) 2021 dated 28 June 2021 with effect from 1 July 2021. APPENDIX 1 OUTSTANDING S$ CREDIT FACILITY (To be submitted online) AS AT END OF (month) Name of Capital Markets Services Licence Holder____________________ Officer-in-charge ____________________ (Tel) ____________________ S$ CREDIT FACILITIES

---

## gs-0103 · temporal · confidence 1.0

**Q.** When did the cancellation of the notices on Technology Risk Management and Cyber Hygiene take effect?

**A.** The cancellation of those specific notices took effect from 10 May 2024.

**Gold span** — Notice 127 Technology Risk Management [Cancelled] · clause 2

> The following Notices are cancelled with effect from 10 May 2024: (a) MAS Notice 127 'Notice on Technology Risk Management' dated 21 June 2013; (b) MAS Notice 132 'Notice on Cyber Hygiene' dated 6 August 2019; (c) MAS Notice 506 'Notice on Technology Risk Management' dated 21 June 2013; (d) MAS Notice 507 'Notice on Cyber Hygiene' dated 6 August 2019.

---

## gs-0104 · temporal · confidence 1.0

**Q.** What was the effective date for the cancellation of the notices regarding technology risk management and cyber hygiene?

**A.** The cancellation of the notices on technology risk management and cyber hygiene took effect from 10 May 2024.

**Gold span** — Notice 834 Cyber Hygiene [Cancelled] · clause 2

> The following Notices are cancelled with effect from 10 May 2024: (a) MAS Notice 830 'Notice on Technology Risk Management' dated 21 June 2013; (b) MAS Notice 834 'Notice on Cyber Hygiene' dated 6 August 2019.

---

## gs-0105 · temporal · confidence 1.0

**Q.** When did the updated investment policy requirements for FHC groups come into force?

**A.** The new provisions started applying on 1 January 2025.

**Gold span** — Notice FHC-N125 Investment Activities · clause Notes on History of Amendments/1

> MAS Notice FHC-125 (Amendment) 2024 dated 3 December 2024 with effect from 1 January 2025. Appendix A Main Elements of Written Investment Policy for an FHC Group The written investment policy for an FHC group must include the following: 1 Policy relating to the determination of the strategic asset allocation. This must be done with due regard to asset-liability management 3 , overall risk tolerance 4 , long-term riskreturn requirements and the respective solvency positions of the DFHC (Licensed Insurer) and other entities within the FHC group. [MAS Notice FHC-N125 (Amendment) 2024] 2 Policy relating to the establishment of limits for the allocation of assets by type of asset, credit rating, geographical area, markets, sectors, counterparties and currency for the FHC group. In establishing the limits, a DFHC (Licensed Insurer) must ensure adequate diversification within a risk category an

---

## gs-0106 · temporal · confidence 1.0

**Q.** When did the cancellation of the notices on technology risk management and cyber hygiene take effect?

**A.** These notices were cancelled with effect from 10 May 2024.

**Gold span** — Notice on Cyber Hygiene for Licensed Credit Bureaus [Cancelled] · clause 2

> The following Notices are cancelled with effect from 10 May 2024: (a) MAS Notice CBN02 'Notice on Technology Risk Management' dated 28 May 2021; (b) MAS Notice CBN03 'Notice on Cyber Hygiene' dated 28 May 2021.

---

## gs-0107 · temporal · confidence 1.0

**Q.** When was the provision regarding exposure calculation for index options removed from the regulations?

**A.** The specific requirement concerning index options was deleted by MAS Notice 656 (Amendment) 2024.

**Gold span** — Notice 656 Exposures to Single Counterparty Groups for Banks Incorporated in Singapore · clause 3.9

> A Reporting Bank must calculate the exposure value of an investment in index positions, securitisations, hedge funds or investment funds held in the trading book applying the same approach as for similar instruments held in the banking book in accordance with paragraphs 4.4 to 4.16 of this Annex. Accordingly, the Reporting Bank may assign the amount invested in a particular structure to - (a) the structure itself, where it is defined as a distinct counterparty; (b) the counterparties corresponding to the underlying assets; or (c) the unknown client described in paragraph 4.11(b) of this Annex. 8 For example, an index option. 9 [Deleted by MAS Notice 656 (Amendment) 2024] 10 [Deleted by MAS Notice 656 (Amendment) 2024] [MAS Notice 656 (Amendment) 2024]

---

## gs-0108 · temporal · confidence 1.0

**Q.** When did the amendment regarding excluded warrants take effect?

**A.** The requirements listed in this appendix came into force on 28 July 2023.

**Gold span** — Notice SFA 02-N01 Listing, De-Listing or Trading of Relevant Products on an Organised Market of an Approved Exchange or a Recognised Market Operator Incorporated in Singapore · clause 2

> SFA 02-N01 (Amendment) 2023 with effect from 28 July 2023. Appendix 1 Part 1 - List of Excluded Warrants The following instruments are excluded warrants: (a) a daily leverage certificate of which the underlying thing is - (i) any share of a corporation that is listed on a specified exchange; (ii) any unit in a business trust that is listed on a specified exchange; (iii) any unit in a collective investment scheme that is listed on a specified exchange; or (iv) any securities index comprising shares or units mentioned in paragraph (i), (ii) or (iii) above; (b) a structured certificate of which the underlying thing is - (i) any share of a corporation that is listed on a specified exchange; (ii) any unit in a business trust that is listed on a specified exchange; (iii) any unit in a collective investment scheme that is listed on a specified exchange; or (iv) any securities index comprising s

---

## gs-0109 · temporal · confidence 1.0

**Q.** When did the over-collateralisation requirement for qualifying covered bonds change to include regulatory CRE exposures with a 100% risk weight, and what amendment effected this change?

**A.** The requirement was amended by MAS Notice 656 (Amendment) 2024 to allow regulatory CRE exposures with a 100% or lower risk weight as part of the cover pool for qualifying covered bonds.

**Gold span** — Notice 656 Exposures to Single Counterparty Groups for Banks Incorporated in Singapore · clause 4.3

> For the purposes of paragraph 4.2 of this Annex, a qualifying covered bond refers to a covered bond that meets the following conditions at the inception date of the covered bond and throughout its remaining maturity: (a) the cover pool of the covered bond consists of assets that constitute - 31 (i) exposures which would fall within the central government and central bank asset class, PSE asset class or MDB asset class under the SA(CR) in accordance with paragraph 7.3.1(b) to (d) of Part VII of MAS Notice 637; (ii) regulatory RRE exposures which would fall within the regulatory real estate asset sub-class under the SA(CR) in accordance with paragraph 7.3.1(k)(ii) of Part VII of MAS Notice 637 that would - (A) qualify for a 35% or lower risk weight under the SA(CR) set out in paragraphs 7.3.91 to 7.3.92 and subject to paragraph 7.3.96 of Part VII of MAS Notice 637; and (B) have a loan-to-v

---

## gs-0110 · temporal · confidence 1.0

**Q.** When was the item regarding income and expenses removed from the notice's scope, and which specific amendment caused that change?

**A.** The provision concerning income and expenses was deleted by MAS Notice 306 (Amendment) 2021, meaning it no longer applies under the current version of this guidance.

**Gold span** — Notice 306 Market Conduct Standards for Life Insurers Providing Financial Advisory Services as defined under the Financial Advisers Act · clause 2

> This Notice covers the following: (a) Appointment of Representatives (b) Maximum Tier Structure (c) Training and Competency of Representatives (d) Loans and Advances to Representatives (e) Compliance Unit (f) Disciplinary Action (g) Income and Expenses [Deleted by MAS Notice 306 (Amendment) 2021]

---

## gs-0111 · temporal · confidence 1.0

**Q.** When must a digital token service provider update its internal policies and procedures?

**A.** The document requires updates to be made in a timely manner to address new operational, legal, regulatory developments, or emerging ML/TF risks.

**Gold span** — Guidelines to MAS Notice FSM-N27 on Prevention of Money Laundering and Countering the Financing of Terrorism - Digital Token Service Providers · clause 18

> 18-1 As internal policies and procedures serve to guide employees, officers and representatives in ensuring compliance with AML/CFT laws and regulations, it is important that a digital token service provider updates its policies and procedures in a timely manner, to take into account new operational, legal and regulatory developments and emerging or new ML/TF risks. Notice Paragraphs 18.3 to 18.10 18-2 Group Policy 18-2-1 In relation to paragraph 18.6 of the Notice, examples of the types of information that should be shared within the financial group for risk management purposes are positive name matches arising from screening performed against ML/TF information sources, a list of customers who have been exited by the digital token service provider, its branches and subsidiaries based on suspicion of ML/TF and names of parties on whom STRs have been filed. Such information should be shar

---

## gs-0112 · temporal · confidence 1.0

**Q.** When did the guidelines on the valuation of policy liabilities relating to life business take effect?

**A.** These guidelines took effect from 31 March 2026.

**Gold span** — Notice 133 Valuation and Capital Framework for Insurers · clause 8

> MAS Notice 133 (Amendment) 2026 dated 16 March 2026 with effect from 31 March 2026. Appendix 3A GUIDELINES ON THE VALUATION OF POLICY LIABILITIES RELATING TO THE LIFE BUSINESS OF AN INSURER DATA AND VALUATION SYSTEM

---

## gs-0114 · temporal · confidence 1.0

**Q.** When did the cancellation of these specific notices take effect?

**A.** The cancellation of these notices took effect from 10 May 2024.

**Gold span** — Notice 644A Technology Risk Management [Cancelled] · clause 2

> The following Notices are cancelled with effect from 10 May 2024: (a) MAS Notice 644 'Notice on Technology Risk Management' dated 21 June 2013; (b) MAS Notice 655 'Notice on Cyber Hygiene' dated 6 August 2019; (c) MAS Notice 644A 'Notice on Technology Risk Management' dated 21 June 2013; (d) MAS Notice 655A 'Notice on Cyber Hygiene' dated 6 August 2019; (e) MAS Notice 1114 'Notice on Technology Risk Management' dated 1 July 2021; (f) MAS Notice 1118 'Notice on Cyber Hygiene' dated 1 July 2021.

---

## gs-0115 · temporal · confidence 1.0

**Q.** When was this specific paragraph removed from the rules?

**A.** This provision was deleted by the regulatory amendment issued in 2024.

**Gold span** — Notice 656 Exposures to Single Counterparty Groups for Banks Incorporated in Singapore · clause 2.1

> A Reporting Bank must calculate the exposure value of its banking book on-balance sheet nonderivative assets based on the carrying amount of such assets as determined in accordance with the Accounting Standards, where such amounts are - 25 (a) net of specific allowances and accounting valuation adjustments attributable to such assets; or (b) gross of any specific allowance and accounting valuation adjustments. Pre-settlement counterparty exposure for derivative transactions and long settlement transactions 2.2 A Reporting Bank must calculate the exposure value for the pre-settlement counterparty exposure to a counterparty arising from the following: (a) OTC derivative transactions; (b) exchange-traded derivative transactions; (c) long settlement transactions that are not SFTs, whether or not such transactions are classified as banking book or trading book exposures based on the SA-CCR se

---

## gs-0116 · negative · confidence 1.0

**Q.** What are the Minimum and Best Practice Training and Competency Standards for Direct General Insurers as specified by the Hong Kong Monetary Authority?

**A.** This information cannot be answered from the provided corpus because it contains only Singapore MAS notices and guidelines, which do not include regulatory standards issued by the Hong Kong Monetary Authority.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0117 · negative · confidence 1.0

**Q.** What are the statutory penalties under the Proceeds of Crime Act for a person who fails to comply with a money laundering control order issued by a court?

**A.** This specific statutory penalty is not addressed in MAS notices or guidelines because it is defined directly within the text of the Proceeds of Crime Act and related subsidiary legislation, which form the primary legal source for such penalties rather than MAS supervisory documents.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0119 · negative · confidence 1.0

**Q.** What specific percentage of unitholder consent is required under Notice 1018 to approve a restructuring of the underlying assets for a Private Equity fund?

**A.** This information is not addressed in MAS notices or guidelines because the regulatory framework for private equity funds does not prescribe a fixed numerical threshold for unitholder consent on asset restructuring, leaving such procedural details to be determined by the individual fund's offering document and trust deed.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0120 · negative · confidence 1.0

**Q.** In relation to our deposit-taking activities, does the Deposit Insurance Corporation require financial institutions to report on the energy efficiency metrics of their data centre operations as part of the DIA-N01 Deposit Insurance Returns submission?

**A.** This matter is not addressed in MAS notices or guidelines because the Singapore Deposit Insurance Corporation (SDIC) regulates deposit insurance coverage and claims, not operational environmental standards such as data centre energy use.

**Claimed unanswerable because:** `unregulated_topic`

---

## gs-0121 · negative · confidence 1.0

**Q.** Given the cancellation of MAS Notice 1119 regarding cyber hygiene standards, what specific equivalent mandatory requirements for third-party risk management and supply chain security audits are currently enforced by the Hong Kong Monetary Authority under its Code of Banking Practice?

**A.** This question cannot be answered using only MAS notices and guidelines because those documents exclusively cover Singapore regulatory obligations and do not contain information about the specific enforcement actions or mandatory audit frequencies set by the Hong Kong Monetary Authority.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0122 · negative · confidence 1.0

**Q.** What are the statutory penalties prescribed under the relevant Act for non-compliance with the provisions on financial statement disclosure found in Notice 608?

**A.** This information is not available because the specific statutory penalties and sections of the Act are established by legislation, whereas the MAS corpus contains only notices and guidelines that do not define criminal or civil penalties.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0123 · negative · confidence 1.0

**Q.** Under Notice PSN01 Prevention of Money Laundering and Countering the Financing of Terrorism – Specified Payment Services, what specific obligations must a financial institution fulfill today regarding customer due diligence for cross-border remittances?

**A.** This question cannot be answered from MAS notices or guidelines because the specified instrument has been cancelled or withdrawn, meaning its requirements are no longer in force and do not constitute current regulatory obligations.

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0124 · negative · confidence 1.0

**Q.** According to Notice 1005A, what specific percentage of the outstanding credit facility limit must be provisioned for a borrower whose financial difficulties are expected to persist beyond six months under the temporary relief framework?

**A.** The required specific percentage is not addressed in MAS notices or guidelines because the regulatory framework does not mandate a fixed provisioning percentage based solely on the duration of difficulty, leaving such calculation methodology to the institution's own internal policies.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0125 · negative · confidence 1.0

**Q.** Under the current regulatory framework administered by the Monetary Authority of Singapore, are financial institutions required to submit quarterly energy consumption reports detailing the kilowatt-hour usage of their primary data centre facilities for external auditing purposes?

**A.** This inquiry cannot be answered from MAS notices or guidelines because the Monetary Authority of Singapore does not regulate or mandate reporting standards for corporate data centre energy efficiency or general facility utility consumption.

**Claimed unanswerable because:** `unregulated_topic`

---

## gs-0126 · negative · confidence 1.0

**Q.** Does the requirement for submission of statistics and returns under Notice FHC-N610 align with similar reporting obligations imposed by the Hong Kong Monetary Authority on local banks?

**A.** This question cannot be answered using MAS notices and guidelines because these documents do not contain information regarding the specific regulatory requirements or alignment standards set by the Hong Kong Monetary Authority.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0127 · negative · confidence 1.0

**Q.** Under the Securities and Futures Act, what specific statutory penalty applies for a dealer who fails to maintain an accurate register of dealers as required by Notice 753?

**A.** This specific statutory penalty is not addressed in MAS notices or guidelines because such documents do not contain provisions of the Securities and Futures Act itself, which is where penalties are defined.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0128 · negative · confidence 1.0

**Q.** Under Notice FAA-N27 Reporting of Misconduct of Representatives by Financial Advisers, what specific reporting timelines and content requirements apply to a firm today for misconduct occurring between now and January 1, 2027?

**A.** This cannot be answered from the MAS corpus because the provided notice is explicitly effective only from 1 January 2027, meaning it contains no provisions or requirements applicable to reporting obligations before that date.

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0129 · negative · confidence 1.0

**Q.** What is the specific minimum percentage of shareholder ownership required for a Singapore Variable Capital Company (VCC) to be classified as an 'eligible investment company' under the Prevention of Money Laundering and Countering the Financing of Terrorism framework?

**A.** This specific threshold is not addressed in MAS notices or guidelines because the regulatory definition of an 'eligible investment company' relies on qualifying criteria set out in the Securities and Futures Act rather than a fixed ownership percentage stipulated in MAS AML/CFT notices.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0130 · negative · confidence 1.0

**Q.** Under the consolidated supervision framework outlined in Notice 625 regarding Sections 31 and 33, are there any specific exemptions for a financial group where a subsidiary's employment contract includes a mandatory clause requiring all employees to reside within the Republic for the duration of their service?

**A.** This matter is not addressed in MAS notices or guidelines because employment residency requirements and labor contract clauses fall under the jurisdiction of the Ministry of Manpower, not the Monetary Authority of Singapore.

**Claimed unanswerable because:** `unregulated_topic`

---

## gs-0131 · negative · confidence 1.0

**Q.** According to Notice 755 on weekly S$ transaction reporting, what specific thresholds and formats does the Hong Kong Monetary Authority require for cross-border trade reporting from Singapore to Hong Kong?

**A.** This requirement is not addressed in MAS notices or guidelines because they exclusively cover Singapore regulatory mandates and do not contain information regarding the operational standards or reporting thresholds imposed by the Hong Kong Monetary Authority.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0132 · negative · confidence 1.0

**Q.** Under which section of the Banking Act does the Monetary Authority of Singapore impose a statutory fine for operating without a banking license, and what is the maximum penalty prescribed by the courts?

**A.** This information is not addressed in MAS notices or guidelines because they do not contain the primary statutory provisions or specific court-determined penalties found in the Banking Act.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0133 · negative · confidence 1.0

**Q.** Under Notice 834 Cyber Hygiene, what specific technical controls must a financial institution implement to ensure its third-party vendors meet the minimum cybersecurity standards for remote access?

**A.** This is not addressed in MAS notices or guidelines because the referenced document, 'Notice 834 Cyber Hygiene', has been officially cancelled and withdrawn from the regulatory corpus.

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0134 · negative · confidence 1.0

**Q.** For a licensed credit bureau classified as 'high risk' under the Technology Risk Management framework, does MAS Notice require the appointment of a dedicated Chief Information Security Officer by a specific deadline and mandate that 100% of annual revenue be allocated to cybersecurity training?

**A.** This is not addressed in MAS notices or guidelines because the referenced document has been cancelled and the current active regulatory text does not contain these specific requirements regarding high-risk classification thresholds, CISO appointment deadlines, or mandatory revenue allocation percentages for cybersecurity training.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0135 · negative · confidence 1.0

**Q.** In accordance with the technology risk management framework outlined in Notice FSM-N03, what are the specific regulatory requirements for an institution's internal policies regarding employee overtime compensation and annual income tax filing deadlines?

**A.** This matter is not addressed in MAS notices or guidelines because employment law and individual income tax obligations fall entirely under the jurisdiction of the Ministry of Manpower and the Inland Revenue Authority of Singapore, respectively, and are outside the scope of financial regulation.

**Claimed unanswerable because:** `unregulated_topic`

---

## gs-0136 · negative · confidence 1.0

**Q.** According to the principles outlined in MAS Notice 635 on Unsecured Credit Facilities to Individuals, how does the Hong Kong Monetary Authority specifically define the 'reasonable steps' a lender must take to verify an individual's ability to repay before granting credit?

**A.** This query cannot be answered from MAS notices or guidelines because those documents exclusively contain Singapore regulatory requirements and do not include specific definitions or enforcement actions issued by the Hong Kong Monetary Authority.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0137 · negative · confidence 1.0

**Q.** Under what specific section of the Act is a financial institution liable to a court-ordered penalty for failing to file a reinsurance declaration within 30 days of entering an agreement?

**A.** This inquiry cannot be answered from MAS notices or guidelines because such documents only provide supervisory expectations and do not contain statutory provisions, specific court remedies, or the exact sections of Acts that define legal liabilities and penalties.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0138 · negative · confidence 1.0

**Q.** Under Notice 1111 Risk Based Capital Adequacy Requirements for Merchant Banks Incorporated in Singapore, what specific liquidity coverage ratio minimums must a merchant bank maintain today?

**A.** This question is not addressed in MAS notices or guidelines because the referenced document 'Notice 1111' specifically pertains to capital adequacy requirements and does not contain provisions regarding liquidity coverage ratio minimums.

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0139 · negative · confidence 1.0

**Q.** What is the specific maximum percentage of a client's portfolio that an exempt person is permitted to hold without obtaining prior written consent from the Securities and Futures Authority under Notice SFA 04-N07?

**A.** This specific numerical threshold is not addressed in MAS notices or guidelines, as the regulation focuses on prohibited representations rather than establishing quantitative limits on portfolio holdings for exempt persons.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0140 · negative · confidence 1.0

**Q.** In light of our primary dealer obligations under Notice 762, does the requirement to maintain segregation of client funds extend to covering liabilities arising from workplace ergonomic injuries sustained by front-office staff?

**A.** This issue is not addressed in MAS notices or guidelines because workplace health and safety liabilities for employees are governed by Singapore's Employment Act and related labour laws, not by financial market conduct regulations.

**Claimed unanswerable because:** `unregulated_topic`

---

## gs-0141 · negative · confidence 1.0

**Q.** Does the Hong Kong Monetary Authority impose a similar prohibition on the circulation of 10,000 Singapore Dollars denominated currency notes within its jurisdiction?

**A.** This matter is not addressed in the provided corpus because it contains only Singapore Monetary Authority notices and guidelines, which do not include regulatory requirements or enforcement actions from the Hong Kong Monetary Authority.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0142 · negative · confidence 1.0

**Q.** What is the statutory penalty under the Banking Act for a bank director who fails to comply with a direction issued by the Monetary Authority under Section 102?

**A.** The specific statutory penalty for non-compliance with a Section 102 direction is not addressed in MAS notices or guidelines because such penalties are defined exclusively within the primary legislation of the Banking Act itself.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0143 · negative · confidence 1.0

**Q.** Under Notice 823 Dealing in Government Securities, what are the current reporting requirements for a financial institution acquiring sovereign bonds issued by an entity other than Singapore's central government?

**A.** This inquiry cannot be answered from MAS notices or guidelines because specific reporting requirements for non-central government sovereign bonds under this instrument are not addressed, and such instruments typically do not cover derivative or secondary market dealings in non-domestic sovereign securities outside their primary scope.

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0144 · negative · confidence 1.0

**Q.** According to the current requirements under Notice 632 Residential Property Loans, what is the specific maximum loan-to-value ratio (LTV) percentage applicable to a second mortgage granted to an individual borrower who is over 70 years of age?

**A.** The MAS does not set a specific LTV threshold for borrowers over 70 years in Notice 632, as this notice primarily establishes the general rule that residential property loans must be fully secured and typically prohibits second mortgages unless strictly necessary for refinancing existing debt.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0145 · negative · confidence 1.0

**Q.** In the context of residential property loan risk assessment under Notice 825B, does MAS provide specific guidance on how to account for energy efficiency ratings and carbon footprint disclosures when evaluating a borrower's long-term debt servicing capacity?

**A.** This is not addressed in MAS notices or guidelines because the Monetary Authority of Singapore does not regulate consumer product safety or building energy performance standards, which fall under the jurisdiction of other agencies such as the Energy Market Authority.

**Claimed unanswerable because:** `unregulated_topic`

---

## gs-0146 · negative · confidence 1.0

**Q.** Under HKMA Notice 2018/61, what specific exemption criteria allow a financial institution to avoid filing a notification for transactions where the related party is a close relative of a director?

**A.** This requirement cannot be answered from MAS notices or guidelines because they exclusively cover Singapore regulatory frameworks and do not contain Hong Kong Monetary Authority documents or their specific exemption criteria.

**Claimed unanswerable because:** `other_jurisdiction`

---

## gs-0147 · negative · confidence 1.0

**Q.** Under which section of the Securities and Futures Act is the statutory penalty for contravening a prohibition order defined, and what specific court remedy is available for enforcement?

**A.** This information is not addressed in MAS notices or guidelines because statutory penalties and specific court remedies are prescribed by the Securities and Futures Act and its subsidiary regulations, which constitute primary legislation rather than regulatory guidance documents.

**Claimed unanswerable because:** `out_of_scope_instrument`

---

## gs-0148 · negative · confidence 1.0

**Q.** Under Notice 824 on Prevention of Money Laundering and Countering the Financing of Terrorism – Finance Companies, what are the specific licensing requirements for a finance company operating in Singapore today?

**A.** This is not addressed in MAS notices or guidelines because the document titled 'Notice 824' does not contain information on licensing requirements; instead, it focuses exclusively on anti-money laundering and counter-terrorist financing obligations applicable to finance companies.

**Claimed unanswerable because:** `withdrawn_requirement`

---

## gs-0149 · negative · confidence 1.0

**Q.** According to the requirements outlined in Notice 319 regarding the valuation of policy liabilities for life business, what is the specific percentage threshold above which a financial institution must immediately apply the IFRS 17 transitional relief provisions when calculating the discount rates for long-duration contracts?

**A.** This specific percentage threshold is not addressed in MAS notices or guidelines because Notice 319 has been cancelled with effect from 31 March 2020 and does not contain such a provision.

**Claimed unanswerable because:** `invented_specific`

---

## gs-0150 · negative · confidence 1.0

**Q.** Under the Prevention of Money Laundering and Countering the Financing of Terrorism Act, are digital asset service providers required to submit quarterly energy consumption reports for their data centre operations as part of their mandatory sustainability disclosures?

**A.** No, this is not addressed in MAS notices or guidelines because the Monetary Authority of Singapore does not regulate corporate carbon footprints or data centre energy usage, which fall under the jurisdiction of other agencies such as the Energy Market Authority or the Environmental Protection Department.

**Claimed unanswerable because:** `unregulated_topic`

---
