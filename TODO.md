# Implementation Plan for RKR Enhancement, Dashboard Mode, and MPS

## Overview
This document outlines the implementation of three major enhancements to the Caner meal recommendation system:

1. **Enhanced RKR (RKR Real) Scoring** - Update penalty system with comprehensive ingredient list
2. **Dashboard Mode** - TV-friendly display showing mensa and Hesse meals side-by-side with integrated Marvin recommendation
3. **Max Pumper Score (MPS)** - AI-powered scoring system based on Max's fitness-focused preferences

## 1. Enhanced RKR Scoring System

### Current State Analysis
- RKR uses protein/price ratio with penalties for certain keywords
- Current penalty keywords: `["gemüse", "erbsen", "bohnen", "champignons", "pilze", "cremige tomatensauce", "mais", "pflanzlich", "vegan", "pilz", "spargel", "broccoli", "karotten"]`
- Special handling: "erbsen" divides score by 10, others divide by 2

### Implementation Tasks

#### 1.1 Update Penalty Keywords List
- Replace current `PENALTY_KEYWORDS` in `app.py` with comprehensive list:
  ```python
  PENALTY_KEYWORDS = [
      # Vegetables
      "zucchini", "paprika", "karotten", "brokkoli", "blumenkohl", "spinat",
      "aubergine", "erbsen", "bohnen", "spargel", "lauch", "sellerie",
      "zwiebeln", "knoblauch", "schalotten", "salat", "rucola", "feldsalat",
      "eisbergsalat",

      # Mushrooms
      "champignons", "pfifferlinge", "steinpilze", "pilze",

      # Fruits
      "äpfel", "birnen", "quitten", "kirschen", "pflaumen", "aprikosen",
      "pfirsiche", "nektarinen", "erdbeeren", "himbeeren", "heidelbeeren",
      "brombeeren", "johannisbeeren", "orangen", "mandarinen", "zitronen",
      "limetten", "grapefruits", "bananen", "ananas", "mango", "kiwi", "melonen",
      "rosinen", "getrocknete pflaumen", "datteln",

      # Fish & Seafood
      "lachs", "thunfisch", "forelle", "kabeljau", "hering",
      "garnelen", "krabben", "muscheln", "austern", "tintenfisch", "hummer",

      # Hidden Vegetables/Fruits
      "gemüseaufläufe", "gratins mit gemüse", "pizza mit gemüse oder pilzen",
      "wraps mit salat", "sandwiches mit gemüse", "burger mit tomaten oder gurken",
      "soßen mit gemüsebasis", "tomatensoße", "ratatouille", "gemüsesuppe",
      "desserts mit obst", "apfelkuchen", "erdbeertorte", "obstsalat",

      # Plant-based Components
      "viel petersilie", "basilikum", "koriander", "dill",
      "soja-fleischalternativen", "gemüse-fleischalternativen",
      "gemüsesäfte", "smoothies", "karottensaft", "multivitaminsaft"
  ]
  ```

#### 1.2 Modify RKR Calculation Logic
- Update `calculate_rkr_real()` function in `app.py`
- Change "erbsen" handling from `rkr_value /= 10` to `rkr_value *= -1`
- Keep other penalties as `rkr_value /= 2`
- Ensure proper case-insensitive matching

#### 1.3 Testing
- Test penalty application with various meal descriptions
- Verify negative scores for erbsen-containing meals
- Check edge cases (multiple penalties, mixed case, etc.)

## 2. Dashboard Mode Implementation

### Current State Analysis
- App displays meals in single-column layout
- Mensa selection filters display
- AI recommendations are modal-based
- No TV-optimized layout

### Implementation Tasks

#### 2.1 Add Dashboard Route Parameter
- Modify `/` route in `app.py` to accept `?dashboard=true` parameter
- Add dashboard-specific logic to show selected mensa + XXXLutz Hesse meals
- Maintain backward compatibility with existing functionality

#### 2.2 Update Template for Dashboard Layout
- Create dashboard-specific layout in `templates/index.html`
- Implement side-by-side display:
  - Left column: Selected mensa meals
  - Right column: XXXLutz Hesse meals
- Ensure responsive design for TV viewing
- Add dashboard-specific CSS classes

#### 2.3 Integrate Marvin Recommendation
- Add prominent Marvin recommendation section to dashboard
- Auto-load Marvin recommendation on dashboard load
- Display as integrated content, not modal
- Ensure recommendation is always visible during dashboard mode

#### 2.4 Dashboard Navigation
- Add toggle between normal and dashboard modes
- Preserve mensa/date selections when switching modes
- Add dashboard mode indicator in UI

#### 2.5 TV-Friendly Optimizations
- Increase font sizes for better TV readability
- Optimize spacing and layout for large screens
- Ensure high contrast and clear visual hierarchy
- Test on various screen sizes

## 3. Max Pumper Score (MPS) Implementation

### Current State Analysis
- Existing AI recommendations use Mistral API
- Meal data stored in database with nutritional information
- No fitness-focused scoring system

### Implementation Tasks

#### 3.1 Database Schema Update
- Add `mps_score` field to `Meal` model in `models.py`
- Add `mps_score` field to `XXXLutzChangingMeal` and `XXXLutzFixedMeal` models
- Create database migration script
- Update data loading functions to handle MPS field

#### 3.2 MPS API Endpoint
- Create `/api/get_mps_score` endpoint in `app.py`
- Implement Mistral API integration for MPS calculation
- Use provided prompt for Max's preferences:
  ```
  Max meidet konsequent alles, was mit Gemüse oder Obst zu tun hat – das betrifft nicht nur offensichtliche Zutaten wie Zucchini, Paprika oder Äpfel, sondern auch Dinge wie Salat, Zwiebeln, Pilze oder Beeren. Auch Fisch lehnt er komplett ab, unabhängig von der Zubereitungsart. Er bevorzugt klare, einfache Gerichte ohne „grünes Zeug“ oder pflanzliche Komponenten, die im Geschmack dominant sind.
  Dafür isst Max gerne herzhafte, proteinreiche Speisen wie Fleischgerichte (z. B. Schwein, Rind, Huhn), Käse oder Eier. Aufgrund seines regelmäßigen Trainings im Fitnessstudio legt er zudem Wert auf einen hohen Proteingehalt, weshalb eiweißreiche Mahlzeiten bei ihm besonders gut ankommen. Neutrale Beilagen wie Reis, Kartoffeln oder Pasta sind für ihn in Ordnung, solange sie nicht mit Gemüse kombiniert sind. Süßspeisen ohne Obst sind ebenfalls gern gesehen.
  ```

#### 3.3 MPS Calculation Logic
- Implement batch MPS calculation for new meals
- Add function to calculate MPS for individual meals
- Handle API rate limits and error cases
- Cache results to avoid redundant API calls

#### 3.4 UI Integration
- Add MPS display to meal cards/tables
- Create MPS-specific visual indicators
- Add MPS to expert mode columns
- Implement color coding for MPS values

#### 3.5 Background Processing
- Add MPS calculation to data loading pipeline
- Implement periodic MPS recalculation for existing meals
- Add logging and monitoring for MPS calculation process

## 4. Additional Enhancements

### 4.1 Performance Optimizations
- Optimize database queries for dashboard mode
- Implement caching for AI recommendations
- Add lazy loading for large meal lists

### 4.2 Error Handling
- Add comprehensive error handling for AI API calls
- Implement fallback displays when AI services are unavailable
- Add user-friendly error messages

### 4.3 Testing and Validation
- Unit tests for RKR calculation logic
- Integration tests for dashboard mode
- API tests for MPS calculation
- Cross-browser and device testing

### 4.4 Documentation
- Update README with new features
- Add API documentation for new endpoints
- Create user guide for dashboard mode

## Implementation Order

1. **Phase 1**: Enhanced RKR Scoring (High priority, independent)
2. **Phase 2**: Dashboard Mode (Medium priority, UI-focused)
3. **Phase 3**: MPS Implementation (High priority, AI integration)
4. **Phase 4**: Performance and Testing (Ongoing)

## Dependencies

- Mistral API access for MPS and existing recommendations
- Database migration capabilities
- Frontend testing on TV/large displays
- Comprehensive meal data for testing penalty system

## Risk Assessment

- **AI API Dependency**: Ensure fallback behavior when Mistral API is unavailable
- **Database Changes**: Test migrations thoroughly to avoid data loss
- **UI Responsiveness**: Verify dashboard works on various screen sizes
- **Performance**: Monitor impact of additional calculations on page load times