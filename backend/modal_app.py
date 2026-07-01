import os
import modal

# 1. Reference our existing cloud storage volume and register the App
model_volume = modal.Volume.from_name("desktriage-model-cache")
app = modal.App("desktriage-inference")

# 2. Define the container software environment
image = (
    modal.Image.debian_slim()
    .pip_install(
        "transformers",
        "peft",
        "accelerate",
        "torch",
        "fastapi"
    )
)

# 3. Define the runner class to keep the model loaded in GPU VRAM
@app.cls(
    image=image,
    gpu="A10G", # Use A10G GPU for fast execution
    volumes={"/cache": model_volume}, # Mount our cached model folder
    env={"HF_HOME": "/cache"},
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    scaledown_window=120 # Shut down after 2 minutes of inactivity to save cost
)
class Model:
    @modal.enter()
    def load_model(self):
        """Runs once when the container boots up to load the model into VRAM."""
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        print("Loading tokenizer and model from volume cache...")
        # Load directly from our storage folder "/cache/desktriage-model"
        self.tokenizer = AutoTokenizer.from_pretrained("/cache/desktriage-model")
        
        # Load the model directly onto the GPU in 16-bit precision (efficient and fast)
        self.model = AutoModelForCausalLM.from_pretrained(
            "/cache/desktriage-model",
            torch_dtype=torch.float16,
            device_map="cuda"
        )
        print("Model successfully loaded onto GPU!")

    @modal.method()
    def generate(self, prompt: str) -> str:
        """Runs on every ticket classification request."""
        import torch

        # Tokenize the pre-formatted prompt directly
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")

        # Set strict generation bounds so it outputs clean JSON
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,  # Keep output deterministic and exact
                do_sample=False
            )
            
        # Decode output (only decode what was generated after the prompt)
        response = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return response.strip()

# 4. Wrap the model class in a standard Web API endpoint (FastAPI)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

web_app = FastAPI()

@web_app.post("/classify")
async def classify_ticket(request: Request):
    """API endpoint that receives requests and hands them to the GPU runner."""
    body = await request.json()
    prompt = body.get("prompt", "")
    
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Missing prompt"})
    
    # Send the prompt to the running GPU class instance
    model_runner = Model()
    response = model_runner.generate.remote(prompt)
    
    return {"result": response}

# Register the web_app endpoint inside Modal
@app.function(image=image)
@modal.asgi_app()
def api():
    return web_app