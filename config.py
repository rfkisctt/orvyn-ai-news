import json
import logging
import os
import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))  # Check every 5 minutes
MAX_ITEMS_PER_POST = int(os.getenv("MAX_ITEMS_PER_POST", "5"))
STORAGE_FILE = os.getenv("STORAGE_FILE", "posted_news.json")
CONFIG_FILE = os.getenv("CONFIG_FILE", "bot_config.json")

EMBED_COLOR = 0x653FDC

RSS_FEEDS = {
    # Official Company Blogs & News
    "OpenAI Blog": "https://openai.com/index/feed.xml",
    "Anthropic Blog": "https://www.anthropic.com/feed.xml",
    "Google AI Blog": "https://ai.google/blog/feed.xml",
    "Google DeepMind Blog": "https://deepmind.google/feed.xml",
    "Meta AI Blog": "https://ai.meta.com/blog/feed/",
    "Microsoft AI Blog": "https://www.microsoft.com/en-us/research/feed/?research_area=artificial-intelligence",
    "NVIDIA Blog": "https://blogs.nvidia.com/feed/",
    "AWS AI Blog": "https://aws.amazon.com/blogs/ai/feed/",
    "Azure AI Blog": "https://azure.microsoft.com/en-us/blog/feed/",
    "Mistral AI Blog": "https://mistral.ai/feed.xml",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "Stability AI": "https://stability.ai/feed",
    "Cohere Blog": "https://cohere.com/blog/feed.xml",
    "xAI News": "https://x.ai/feed",
    "Perplexity Blog": "https://www.perplexity.ai/feed",
    
    # Academic & Research
    "arXiv CS.AI": "https://export.arxiv.org/rss/cs.AI",
    "arXiv CS.CL (NLP)": "https://export.arxiv.org/rss/cs.CL",
    "arXiv CS.LG (ML)": "https://export.arxiv.org/rss/cs.LG",
    "arXiv CS.CV (Vision)": "https://export.arxiv.org/rss/cs.CV",
    "arXiv CS.RO (Robotics)": "https://export.arxiv.org/rss/cs.RO",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    
    # Community & Model Platforms
    "Replicate Blog": "https://replicate.com/blog/feed.xml",
    "Together AI Blog": "https://www.together.ai/blog/feed.xml",
    "LangChain Blog": "https://blog.langchain.dev/rss.xml",
    "LlamaIndex Blog": "https://blog.llamaindex.ai/feed.xml",
    "Ollama Blog": "https://ollama.ai/feed.xml",
    "LM Studio Blog": "https://lmstudio.ai/feed.xml",
    "Fireworks AI": "https://www.fireworks.ai/blog/feed.xml",
    "Modal Blog": "https://modal.com/blog/feed.xml",
    "Groq Blog": "https://groq.com/blog/feed.xml",
    
    # Chinese AI Labs
    "DeepSeek News": "https://www.deepseek.com/feed.xml",
    "Moonshot AI": "https://www.moonshot.cn/feed.xml",
    "Zhipu AI": "https://www.zhipuai.cn/feed.xml",
    
    # Other Notable Sources
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "AI News": "https://artificialintelligence-news.com/feed/",
    "MarkTechPost AI": "https://www.marktechpost.com/category/technology/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/index.xml",
}

MODEL_IMAGES = {
    # OpenAI
    "gpt": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "openai": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "sora": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "o1": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "o3": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "o4": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "chatgpt": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "codex": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "dall-e": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    "dall·e": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg",
    
    # Anthropic
    "claude": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    "anthropic": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    "sonnet": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    "opus": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    "haiku": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    "mythos": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    "fable": "https://avatars.githubusercontent.com/u/149570411?s=200&v=4",
    
    # Google
    "gemini": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    "google": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    "bard": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    "veo": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    "imagen": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    "gemma": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    "deepmind": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Google_Gemini_logo.svg",
    
    # Meta
    "llama": "https://upload.wikimedia.org/wikipedia/commons/8/89/Meta_Platforms_Inc._logo.svg",
    "meta": "https://upload.wikimedia.org/wikipedia/commons/8/89/Meta_Platforms_Inc._logo.svg",
    
    # Mistral
    "mistral": "https://avatars.githubusercontent.com/u/128688530?s=200&v=4",
    "mixtral": "https://avatars.githubusercontent.com/u/128688530?s=200&v=4",
    "codestral": "https://avatars.githubusercontent.com/u/128688530?s=200&v=4",
    "ministral": "https://avatars.githubusercontent.com/u/128688530?s=200&v=4",
    
    # Chinese Labs
    "deepseek": "https://avatars.githubusercontent.com/u/148106734?s=200&v=4",
    "qwen": "https://avatars.githubusercontent.com/u/158137808?s=200&v=4",
    "alibaba": "https://avatars.githubusercontent.com/u/158137808?s=200&v=4",
    "kimi": "https://avatars.githubusercontent.com/u/139194050?s=200&v=4",
    "moonshot": "https://avatars.githubusercontent.com/u/139194050?s=200&v=4",
    "zhipu": "https://avatars.githubusercontent.com/u/114636411?s=200&v=4",
    "chatglm": "https://avatars.githubusercontent.com/u/114636411?s=200&v=4",
    "glm": "https://avatars.githubusercontent.com/u/114636411?s=200&v=4",
    
    # Other
    "grok": "https://avatars.githubusercontent.com/u/173424178?s=200&v=4",
    "xai": "https://avatars.githubusercontent.com/u/173424178?s=200&v=4",
    "perplexity": "https://avatars.githubusercontent.com/u/40273432?s=200&v=4",
    "cohere": "https://avatars.githubusercontent.com/u/85726911?s=200&v=4",
    "stability": "https://avatars.githubusercontent.com/u/74929497?s=200&v=4",
    "stable diffusion": "https://avatars.githubusercontent.com/u/74929497?s=200&v=4",
    "replicate": "https://avatars.githubusercontent.com/u/24359043?s=200&v=4",
}

# Provider URLs for linking
PROVIDER_URLS = {
    "gpt": "https://openai.com",
    "chatgpt": "https://chatgpt.com",
    "sora": "https://openai.com/sora",
    "openai": "https://openai.com",
    "claude": "https://claude.ai",
    "anthropic": "https://www.anthropic.com",
    "gemini": "https://gemini.google.com",
    "google": "https://ai.google",
    "llama": "https://www.meta.com/llama",
    "meta": "https://www.meta.com",
    "mistral": "https://mistral.ai",
    "deepseek": "https://www.deepseek.com",
    "qwen": "https://qwen.alibaba.com",
    "zhipu": "https://www.zhipuai.cn",
    "glm": "https://www.zhipuai.cn",
    "moonshot": "https://www.moonshot.cn",
    "cohere": "https://cohere.com",
    "perplexity": "https://www.perplexity.ai",
    "grok": "https://grok.com",
    "xai": "https://x.ai",
    "stability": "https://stability.ai",
}

# Model/brand names. Updated as new models release monthly.
MODEL_KEYWORDS = [
    # OpenAI
    "gpt-3", "gpt-4", "gpt-5", "gpt5", "chatgpt", "openai", "sora",
    "codex", "dall-e", "dall·e", " o1", " o3", " o4",
    # Anthropic
    "claude", "anthropic", "sonnet", "opus", "haiku", "mythos", "fable",
    # Google
    "gemini", "bard", "google deepmind", "deepmind", "veo", "imagen",
    "gemma",
    # Meta
    "llama", "meta ai", "meta platforms",
    # Mistral
    "mistral", "mixtral", "codestral", "ministral",
    # xAI
    "grok", "xai",
    # Chinese labs
    "deepseek", "qwen", "alibaba", "kimi k2", "moonshot ai",
    "zhipu", "chatglm", "glm-4", "glm-5",
    # Others
    "perplexity ai", "cohere", "command r", "stability ai", "stable diffusion",
    "falcon", "phi-3", "phi-4", "replicate", "together ai",
]

# Action keywords indicating a real launch/update
ACTION_KEYWORDS = [
    "launch", "launches", "launched", "launching",
    "release", "releases", "released", "releasing",
    "unveil", "unveils", "unveiled",
    "debut", "debuts", "debuted",
    "introduce", "introduces", "introduced",
    "roll out", "rolls out", "rolled out",
    "update", "updates", "updated", "upgrade", "upgrades", "upgraded",
    "new version", "now available", "available now",
    "announce", "announces", "announced", "announcement",
    "ships", "shipped", "preview", "open-source", "open sources",
]

# Category detection keywords
CATEGORY_KEYWORDS = {
    "Launch": [
        "launch", "launches", "launched", "launching", "debut",
        "introduce", "introduces", "introduced", "unveil", "unveiled",
        "release", "releases", "released", "now available",
    ],
    "Update": [
        "update", "updated", "upgrade", "upgraded", "improved",
        "enhancement", "enhancements", "new version", "v2", "v3", "v4", "v5",
    ],
    "Research": [
        "paper", "papers", "research", "study", "arxiv", "benchmark",
        "dataset", "evaluation", "findings",
    ],
    "Benchmark": [
        "benchmark", "benchmarked", "performance", "leaderboard",
        "results", "comparison", "vs ",
    ],
    "API": [
        "api", "apis", "endpoint", "integration", "sdk",
        "library", "plugin",
    ],
    "Open Source": [
        "open source", "github", "repository", "source code",
        "open sourced", "apache", "mit license",
    ],
    "Pricing": [
        "pricing", "price", "cost", "free", "subscription",
        "payment", "billing", "credit",
    ],
    "Safety": [
        "safety", "secure", "security", "protection", "vulnerability",
        "jailbreak", "adversarial", "responsible",
    ],
    "Agent": [
        "agent", "agents", "autonomous", "automation",
        "tool use", "action", "planning",
    ],
    "Coding": [
        "code", "coding", "programming", "developer", "software",
        "github", "ide", "copilot",
    ],
    "Image": [
        "image", "images", "vision", "visual", "generate",
        "dall-e", "imagen", "flux",
    ],
    "Video": [
        "video", "videos", "sora", "motion", "temporal",
        "generation", "synthesis",
    ],
    "Voice": [
        "voice", "audio", "speech", "tts", "text-to-speech",
        "voice clone", "speaking",
    ],
    "Robotics": [
        "robot", "robotics", "physical", "embodied",
        "locomotion", "manipulation", "hardware",
    ],
}

AI_MODELS = MODEL_KEYWORDS


def detect_category(text: str) -> str:
    """Detect the news category based on content."""
    text_lower = text.lower()
    scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score
    
    if scores:
        return max(scores, key=scores.get)
    return "News"


def detect_badge_type(text: str) -> tuple[str, str]:
    """Detect if this is a release or update. Returns (badge, type_name)."""
    text_lower = text.lower()
    
    release_words = ["launch", "unveil", "debut", "release", "introduce", "announce"]
    update_words = ["update", "upgrade", "improved", "enhancement"]
    
    release_count = sum(1 for w in release_words if w in text_lower)
    update_count = sum(1 for w in update_words if w in text_lower)
    
    if release_count >= update_count and release_count > 0:
        return "🚀", "Model Release"
    elif update_count > 0:
        return "✨", "Model Update"
    else:
        return "📰", "AI News"


def get_image_url(text: str) -> str:
    text_lower = text.lower()
    for keyword, url in MODEL_IMAGES.items():
        if keyword in text_lower:
            return url
    return "/public/return_logo.png"


def is_model_news(text: str) -> bool:
    """True only if the text mentions a known AI model/brand AND an
    action word (launch/release/update/etc).

    The old version flagged anything containing a single generic word like
    "launch" or "llm", which is why a lot of unrelated articles were
    slipping through. Requiring both makes it much closer to "an AI model
    that actually got launched or updated".
    """
    text_lower = f" {text.lower()} "
    has_model = any(keyword in text_lower for keyword in MODEL_KEYWORDS)
    has_action = any(action in text_lower for action in ACTION_KEYWORDS)
    return has_model and has_action


def is_today_wib(published_parsed) -> bool:
    if not published_parsed:
        return True
    try:
        dt_utc = datetime.datetime(*published_parsed[:6], tzinfo=datetime.timezone.utc)
        dt_wib = dt_utc + datetime.timedelta(hours=7)
        today_wib = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
        return dt_wib.date() == today_wib.date()
    except Exception:
        return True


def _load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Save config error: {e}")


def get_news_channel_id():
    return int(_load_config().get("news_channel_id", os.getenv("NEWS_CHANNEL_ID", "0")))


def set_news_channel_id(channel_id):
    config = _load_config()
    config["news_channel_id"] = channel_id
    _save_config(config)
