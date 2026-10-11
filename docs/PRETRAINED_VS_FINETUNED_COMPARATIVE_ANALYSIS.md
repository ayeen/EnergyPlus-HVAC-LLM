# Comparative Analysis: Pre-trained vs Fine-tuned Mistral Model
## For EnergyPlus VRF HVAC Generation

**Date:** January 2026  
**Author:** Ayeen  
**Repository:** EnergyPlus-HVAC-LLM

---

## Executive Summary

This analysis compares the performance of **Pre-trained Mistral** (general-purpose LLM) and **Fine-tuned Mistral** (domain-specific trained on 500+ VRF examples) for automated EnergyPlus HVAC system generation.

**Key Finding:** Fine-tuned Mistral achieves **100% success rate** across all zone counts (1-20), while pre-trained Mistral fails at **20 zones** even with examples provided.

---

## 1. Model Specifications

| Specification | Fine-tuned Mistral | Pre-trained Mistral |
|---------------|-------------------|---------------------|
| **Base Model** | Mistral-7B-v0.1 | Mistral-small-latest |
| **Parameters** | 7 Billion | ~7 Billion |
| **Training Data** | 500+ VRF IDF examples | General web corpus |
| **Access Method** | Local GPU | Mistral API |
| **Domain Knowledge** | EnergyPlus IDF format | General knowledge |
| **Fine-tuning Focus** | HVACTemplate:System:VRF, HVACTemplate:Zone:VRF | None |

---

## 2. Experimental Design

### Test Scenarios

| Test Case | Zones | Base IDF | Purpose |
|-----------|-------|----------|---------|
| `vrf_single_zone` | 1 | building_with_zones_fixed.idf | Basic functionality |
| `vrf_two_zone` | 2 | building_with_zones_fixed.idf | Multi-zone handling |
| `vrf_multi_zone_office` | 4 | 4ZoneWithShading_Simple_2_NoHVAC.idf | Medium complexity |
| `vrf_large_office` | 10 | large_office_10zone.idf | Large scale |
| `vrf_large_office_20zone` | 20 | large_office_20zone.idf | Maximum scale |

### Test Conditions for Pre-trained Model

1. **Scenario A:** Without examples in prompt
2. **Scenario B:** With simple VRF example in prompt

---

## 3. Results

### 3.1 Fine-tuned Mistral Results

| Test Case | Zones | Iterations | First-try Success | Final Result |
|-----------|-------|------------|-------------------|--------------|
| vrf_single_zone | 1 | **0** | ✅ Yes | ✅ SUCCESS |
| vrf_two_zone | 2 | **0** | ✅ Yes | ✅ SUCCESS |
| vrf_multi_zone_office | 4 | 1 | ❌ No | ✅ SUCCESS |
| vrf_large_office | 10 | **0** | ✅ Yes | ✅ SUCCESS |
| vrf_large_office_20zone | 20 | **0** | ✅ Yes | ✅ SUCCESS |

**Summary:**
- First-try Success Rate: **80%** (4/5)
- Final Success Rate: **100%** (5/5)
- Average Iterations: **0.2**

---

### 3.2 Pre-trained Mistral Results (WITHOUT Examples)

| Test Case | Zones | Format Correct | Valid Output | Result |
|-----------|-------|----------------|--------------|--------|
| Single zone | 1 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| Two zone | 2 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| Four zone | 4 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| Ten zone | 10 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| Twenty zone | 20 | ❌ Wrong | ❌ Invalid | ❌ FAILED |

**Issues Observed:**
- Generates `AirConditioner:VariableRefrigerantFlow` instead of `HVACTemplate:System:VRF`
- Wraps output in markdown code blocks (` ```idf ... ``` `)
- Creates invalid object structures

**Summary:**
- Success Rate: **0%** (0/5)
- Model lacks domain-specific knowledge

---

### 3.3 Pre-trained Mistral Results (WITH Simple Example)

| Test Case | Zones | Format Correct | Zone Count | Clean Output | Pipeline Result |
|-----------|-------|----------------|------------|--------------|-----------------|
| Single zone | 1 | ✅ Yes | ✅ 1/1 | ✅ Yes | ✅ SUCCESS |
| Two zone | 2 | ✅ Yes | ✅ 2/2 | ❌ Markdown | ⚠️ PARTIAL |
| Four zone | 4 | ✅ Yes | ✅ 4/4 | ❌ Markdown | ⚠️ PARTIAL |
| Ten zone | 10 | ✅ Yes | ✅ 10/10 | ❌ Markdown | ⚠️ PARTIAL |
| Twenty zone | 20 | ✅ Yes | ✅ 20/20 | ❌ Extra text | ❌ FAILED |

**Issues Observed at Scale:**
- Adds extra text: "HERE ARE THE VALID ENERGYPLUS IDF OBJECTS..."
- Creates malformed object names
- Inconsistent formatting

**Summary:**
- Success Rate: **20%** (1/5 fully clean)
- Breaking Point: **20 zones**

---

## 4. Comparative Analysis

### 4.1 Success Rate Comparison

```
                    SUCCESS RATE BY ZONE COUNT
                    
Zone Count:     1      2      4      10     20     Overall
─────────────────────────────────────────────────────────
Fine-tuned:    ✅     ✅     ✅     ✅     ✅     100%
               ████████████████████████████████████
               
Pre-trained    ✅     ⚠️     ⚠️     ⚠️     ❌      20%
(w/ example):  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
               
Pre-trained    ❌     ❌     ❌     ❌     ❌       0%
(no example):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

### 4.2 Performance Metrics

| Metric | Fine-tuned | Pre-trained (w/ example) | Pre-trained (no example) |
|--------|-----------|--------------------------|--------------------------|
| **First-try Success** | **80%** | 20% | 0% |
| **Final Success** | **100%** | 20% | 0% |
| **Avg Iterations** | **0.2** | N/A | N/A |
| **Breaking Point** | None | 20 zones | All zones |
| **Output Quality** | Clean | Has artifacts | Wrong format |

### 4.3 Output Quality Analysis

| Quality Aspect | Fine-tuned | Pre-trained |
|----------------|-----------|-------------|
| Correct object types | ✅ Always | ⚠️ Only with examples |
| Clean formatting | ✅ Always | ❌ Adds markdown/text |
| Valid field values | ✅ Learned | ⚠️ Inconsistent |
| Proper zone naming | ✅ Accurate | ⚠️ May malform |
| Pipeline compatible | ✅ Direct use | ❌ Needs cleaning |

---

## 5. Key Findings

### 5.1 Finding 1: Fine-tuning is Essential for Domain-Specific Tasks

The fine-tuned model achieved **100% success rate** across all zone counts (1-20), while the pre-trained model without examples achieved **0%**.

**Implication:** Domain-specific fine-tuning internalizes the required format and field specifications, eliminating the need for extensive prompting.

### 5.2 Finding 2: In-Context Learning Has Scalability Limits

With examples in the prompt, the pre-trained model:
- ✅ Succeeded at 1 zone (simple case)
- ⚠️ Partially succeeded at 2-10 zones (format correct but has artifacts)
- ❌ Failed at 20 zones (breaking point)

**Implication:** In-context learning (few-shot prompting) works for simple cases but fails at complex, large-scale generation tasks.

### 5.3 Finding 3: Output Quality Degrades at Scale

```
OUTPUT QUALITY vs ZONE COUNT (Pre-trained with example)

Quality
  ↑
High │  ●
     │     ●
     │        ●
     │           ●
Low  │              ●
     └───────────────────→ Zones
         1   2   4  10  20
         
Breaking Point: 20 zones
```

### 5.4 Finding 4: Fine-tuned Model Provides Consistent Performance

```
OUTPUT QUALITY vs ZONE COUNT (Fine-tuned)

Quality
  ↑
High │  ●   ●   ●   ●   ●
     │
     │
     │
Low  │
     └───────────────────→ Zones
         1   2   4  10  20
         
No degradation at scale
```

---

## 6. Error Analysis

### 6.1 Pre-trained Model Error Types

| Error Type | Frequency | Example |
|------------|-----------|---------|
| Wrong object type | 100% (no example) | `AirConditioner:VariableRefrigerantFlow` instead of `HVACTemplate:System:VRF` |
| Markdown wrapping | 80% (with example) | ` ```idf ... ``` ` |
| Extra explanatory text | 20% (at scale) | "HERE ARE THE VALID ENERGYPLUS IDF OBJECTS..." |
| Malformed names | 20% (at scale) | `HVACTEMPLATE:THERMOSTAT` (no spaces) |

### 6.2 Fine-tuned Model Error Types

| Error Type | Frequency | Example |
|------------|-----------|---------|
| Out-of-distribution prompt | 20% | "Heat recovery" prompt caused empty response |
| Temperature range issues | Rare | Corrected by Agent 3 |

---

## 7. Efficiency Comparison

| Efficiency Metric | Fine-tuned | Pre-trained |
|-------------------|-----------|-------------|
| Prompt size | Small (~50 tokens) | Large (~500+ tokens with example) |
| API cost | None (local) | Per-token charges |
| Post-processing needed | None | Markdown removal, cleaning |
| Iterations to success | 0.2 avg | N/A (fails at scale) |
| Pipeline integration | Direct | Requires preprocessing |

---

## 8. Research Implications

### 8.1 For EnergyPlus HVAC Automation

1. **Fine-tuning is necessary** for reliable, scalable HVAC generation
2. **Pre-trained models cannot replace** domain-specific training for complex engineering tasks
3. **Multi-agent architecture** (Generator + Corrector) provides robustness

### 8.2 For LLM Applications in Engineering

1. **Domain-specific fine-tuning** outperforms larger general-purpose models
2. **In-context learning has limits** for structured output generation
3. **Quality degrades predictably** with complexity in pre-trained models

---

## 9. Conclusion

| Research Question | Answer |
|-------------------|--------|
| Can pre-trained LLMs generate valid EnergyPlus IDF? | ❌ Not without examples |
| Can in-context learning replace fine-tuning? | ❌ Fails at scale (20+ zones) |
| Is fine-tuning worth the effort? | ✅ Yes, 100% vs 20% success |
| What is the breaking point for pre-trained? | 20 zones |

### Final Conclusion

Domain-specific fine-tuning of a smaller model (7B parameters) significantly outperforms general-purpose pre-trained models for specialized EnergyPlus HVAC generation tasks. Fine-tuning achieves **100% success across all scales** while pre-trained models fail at **20 zones** even with examples provided.

---

## 10. Files and Resources

| Resource | Location |
|----------|----------|
| Test configurations | `config/hvac_requests.json` |
| Model settings | `config/settings.py` |
| Test results | `outputs/professor_scalability_test.json` |
| Research documentation | `docs/` |

---

**Document Version:** 1.0  
**Last Updated:** January 2026  
**Author:** Ayeen
