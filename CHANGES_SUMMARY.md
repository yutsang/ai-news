# Changes Summary - Fixes Applied

This document summarizes the fixes applied to address the reported issues.

## Issues Fixed

### 1. ✅ Trans_Commercial Floor/Unit Not Correct (洋房 Case)

**Problem**: Floor and unit parsing was incorrect for 洋房 (house) properties.

**Solution**: Updated `centaline_parser.py` to properly handle 洋房 cases.

**Changes**:
- File: `utils/centaline_parser.py`
- Function: `_parse_property_details()`
- Added special handling for 洋房 pattern detection
- Format: "葡萄園 1期 瑪歌大道 洋房19" → Property: "葡萄園 1期 瑪歌大道", Floor: "洋房", Unit: "19"

**Example**:
```
Before: Property: "葡萄園 1期 瑪歌大道 洋房19", Floor: "N/A", Unit: "N/A"
After:  Property: "葡萄園 1期 瑪歌大道", Floor: "洋房", Unit: "19"
```

### 2. ✅ News Deduplication After Limiting to 20

**Problem**: News articles needed better deduplication when limiting to 20 items.

**Solution**: Improved the deduplication workflow with more aggressive AI-based comparison.

**Changes**:
- File: `utils/excel_formatter.py`
- Updated deduplication order:
  1. Space-normalized topic deduplication (removes exact duplicates)
  2. **AI-based similarity check** (removes highly similar articles)
  3. Ranking by market relevance (keeps top 15-20)

**Key Improvements**:
- AI compares ALL articles (not just within date groups)
- Pre-check for topic overlap before AI call (saves API calls)
- More thorough comparison of summaries
- Filters to keep 15-20 most market-relevant articles

**Workflow**:
```
Original news → Space dedup → AI dedup → Rank & filter → Final 15-20 articles
```

### 3. ✅ Midland ICI Date Not Correct

**Problem**: Dates from Midland ICI API were not formatted correctly.

**Solution**: Updated date parsing to convert YYYY-MM-DD to DD/MM/YYYY format.

**Changes**:
- File: `utils/midland_api_scraper.py`
  - Function: `parse_transaction()`
  - Converts API date from "2025-12-13" to "13/12/2025"
  
- File: `utils/midland_parser.py`
  - Function: `_parse_transaction_block()`
  - Added better date format handling for YYYY/MM/DD input

**Example**:
```
Before: date: "2025-12-13" (YYYY-MM-DD)
After:  date: "13/12/2025" (DD/MM/YYYY)
```

### 4. ✅ PC Local AI Support

**Problem**: Scraper only worked with cloud API, needed support for local AI on PC.

**Solution**: Added full support for local AI servers with OpenAI-compatible APIs.

**Changes**:

1. **config.yml**:
   - Added `chat_model` field for flexibility
   - Added comments explaining cloud vs local AI setup
   - Supports custom `api_base` URL

2. **utils/ai_categorizer.py**:
   - Updated to use `base_url` parameter in OpenAI client
   - Supports both `model` and `chat_model` config fields
   - Defaults for local AI compatibility

3. **utils/detail_extractor.py**:
   - Same updates as ai_categorizer.py
   - Works with any OpenAI-compatible endpoint

4. **utils/excel_formatter.py**:
   - Updated AI client initialization
   - Works with local or cloud AI seamlessly

**How to Use**:

**Cloud AI (DeepSeek)**:
```yaml
deepseek:
  api_key: "sk-your-key"
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"
```

**Local AI (PC)**:
```yaml
deepseek:
  api_key: "local-key"
  api_base: "http://localhost:1234/v1"
  model: "llama3"
  chat_model: "llama3"
```

**Compatible with**:
- LM Studio (http://localhost:1234/v1)
- Ollama (http://localhost:11434/v1)
- LocalAI (http://localhost:8080/v1)
- Text Generation WebUI (http://localhost:5000/v1)
- Any OpenAI-compatible API server

## Files Modified

1. ✅ `utils/centaline_parser.py` - 洋房 floor/unit parsing
2. ✅ `utils/midland_parser.py` - Date format handling
3. ✅ `utils/midland_api_scraper.py` - Date format conversion
4. ✅ `utils/ai_categorizer.py` - Local AI support
5. ✅ `utils/detail_extractor.py` - Local AI support
6. ✅ `utils/excel_formatter.py` - AI dedup + local AI support
7. ✅ `config.yml` - Added chat_model field and comments

## New Documentation

- ✅ `LOCAL_AI_SETUP.md` - Complete guide for PC local AI setup
- ✅ `CHANGES_SUMMARY.md` - This file

## Testing Recommendations

### Test Floor/Unit Parsing
```bash
# Check centaline_data.txt for 洋房 entries
# Run scraper and verify Trans_Commercial sheet has correct Floor/Unit columns
```

### Test Date Formatting
```bash
# Run scraper and check Trans_Commercial sheet
# All dates should be DD/MM/YYYY format
```

### Test News Deduplication
```bash
# Run with a date range that has many news articles
python main.py --start-date 2026-01-01 --end-date 2026-01-07
# Check that news sheet has ~15-20 unique, high-quality articles
```

### Test Local AI
```bash
# Update config.yml with local AI settings
# Run with --quick flag for faster testing
python main.py --start-date 2026-01-01 --end-date 2026-01-07 --quick
```

## Backward Compatibility

✅ All changes are backward compatible:
- Existing cloud API configurations continue to work
- No breaking changes to data formats
- Optional `chat_model` field (falls back to `model`)
- Improved deduplication doesn't break existing workflow

## Next Steps

1. Test with real data to verify all fixes work correctly
2. Monitor AI deduplication quality
3. Adjust ranking scores if needed for news relevance
4. Test with various local AI models for performance

## Support

For issues or questions:
1. Check `LOCAL_AI_SETUP.md` for local AI configuration
2. Verify `config.yml` settings match your setup
3. Test with `--quick` flag for faster debugging
