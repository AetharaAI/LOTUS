# Computer Vision Integration for LOTUS

## Architecture

### Vision Provider (lib/providers.py)
- Claude 3.5 Sonnet (best vision model currently)
- GPT-4V (fallback)
- LLaVA (local via Ollama)

### Vision Module
```python
class VisionModule(BaseModule):
    """Computer vision capabilities"""
    
    @tool
    async def analyze_screenshot(self, image_path: str) -> Dict:
        """Analyze screenshot with Claude"""
        # Read image, encode base64
        # Send to vision provider
        # Return analysis
        
    @tool
    async def read_screen_text(self, image_path: str) -> str:
        """OCR - extract text from image"""
        
    @tool  
    async def detect_ui_elements(self, image_path: str) -> List[UIElement]:
        """Detect buttons, inputs, etc"""
```

### Integration with Reasoning
```python
# In reasoning/logic.py ReAct loop:
if task_requires_vision(user_input):
    screenshot = await perception.capture_screen()
    analysis = await vision.analyze_screenshot(screenshot)
    # Use analysis in reasoning
```

## Usage Example
```
User: "What's on my screen?"
  ↓
Perception → captures screenshot
  ↓
Vision Module → Claude analyzes
  ↓
Reasoning → "You have Chrome open with 3 tabs..."
```
