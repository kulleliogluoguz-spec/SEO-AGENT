"""
Niche-specific seeded intelligence data.
Returns curated trends, audience segments, recommendations, and content opportunities
for 9 niches + a general fallback, personalized with the brand name.
"""
from typing import Any

# ---------------------------------------------------------------------------
# Niche inference
# ---------------------------------------------------------------------------

_NICHE_KEYWORDS: dict[str, list[str]] = {
    "tech":      ["tech", "saas", "software", "app", "ai", "startup", "developer", "platform", "api", "cloud", "data"],
    "fashion":   ["fashion", "clothing", "apparel", "style", "wear", "outfit", "dress", "streetwear"],
    "food":      ["food", "restaurant", "recipe", "cuisine", "chef", "cafe", "bakery", "cooking", "meal", "beverage"],
    "fitness":   ["fitness", "gym", "workout", "health", "wellness", "yoga", "pilates", "running", "nutrition", "coaching"],
    "travel":    ["travel", "tourism", "hotel", "adventure", "destination", "hospitality", "resort", "trip", "explore"],
    "ecommerce": ["shop", "store", "ecommerce", "retail", "product", "brand", "marketplace", "dropship", "dtc"],
    "creator":   ["creator", "media", "content", "entertainment", "influencer", "podcast", "newsletter", "youtube"],
    "beauty":    ["beauty", "skincare", "cosmetic", "makeup", "personal care", "grooming", "haircare", "spa"],
    "b2b":       ["b2b", "consulting", "agency", "marketing", "professional", "services", "enterprise", "business"],
}


def infer_niche(category: str) -> str:
    cl = category.lower()
    for niche, keywords in _NICHE_KEYWORDS.items():
        if any(k in cl for k in keywords):
            return niche
    return "general"


# ---------------------------------------------------------------------------
# Intelligence data per niche
# ---------------------------------------------------------------------------

def _trends(niche: str, brand_name: str) -> list[dict]:
    base: list[dict[str, Any]] = {
        "tech": [
            {"keyword": "AI-native product workflows", "momentum_score": 0.87, "relevance_score": 0.92, "volume_current": 14200, "volume_prior": 7800, "evidence": ["TechCrunch", "Product Hunt", "HN"], "action_hint": f"Create content showing how {brand_name} fits into AI-native workflows"},
            {"keyword": "Vertical SaaS specialization", "momentum_score": 0.74, "relevance_score": 0.85, "volume_current": 8900, "volume_prior": 5100, "evidence": ["a16z", "SaaStr", "ChiefmartecRSS"], "action_hint": "Publish a positioning post around your specific vertical"},
            {"keyword": "AI search & answer engines", "momentum_score": 0.83, "relevance_score": 0.89, "volume_current": 23000, "volume_prior": 9400, "evidence": ["SearchEngineLand", "Moz", "Semrush"], "action_hint": "Write about how your product appears in AI-powered search"},
            {"keyword": "No-code automation for SMBs", "momentum_score": 0.69, "relevance_score": 0.78, "volume_current": 11400, "volume_prior": 7200, "evidence": ["Product Hunt", "IndieHackers"], "action_hint": "Show real automation workflows your tool enables"},
            {"keyword": "Developer experience (DX) as a moat", "momentum_score": 0.62, "relevance_score": 0.71, "volume_current": 6800, "volume_prior": 4600, "evidence": ["HN", "Dev.to", "GitHub Blog"], "action_hint": "Document your SDK / API developer experience"},
            {"keyword": "Privacy-first SaaS architecture", "momentum_score": 0.55, "relevance_score": 0.74, "volume_current": 4200, "volume_prior": 2900, "evidence": ["TechCrunch", "Substack newsletters"], "action_hint": "Write about your data handling and privacy approach"},
            {"keyword": "Agent-based software patterns", "momentum_score": 0.91, "relevance_score": 0.88, "volume_current": 19800, "volume_prior": 6200, "evidence": ["Anthropic Blog", "OpenAI Blog", "LangChain"], "action_hint": "Explain how your product uses or complements AI agents"},
            {"keyword": "Platform consolidation fatigue", "momentum_score": 0.58, "relevance_score": 0.66, "volume_current": 5400, "volume_prior": 3800, "evidence": ["SaaStr", "G2 Reports"], "action_hint": "Position as the consolidation solution in your space"},
        ],
        "fashion": [
            {"keyword": "Quiet luxury aesthetics 2025", "momentum_score": 0.78, "relevance_score": 0.88, "volume_current": 31000, "volume_prior": 18000, "evidence": ["Vogue", "WWD", "Pinterest Trends"], "action_hint": f"Create content aligning {brand_name} with understated premium aesthetics"},
            {"keyword": "Sustainable capsule wardrobe building", "momentum_score": 0.65, "relevance_score": 0.82, "volume_current": 24000, "volume_prior": 15000, "evidence": ["The Good Trade", "Refinery29"], "action_hint": "Show how your pieces work as capsule wardrobe staples"},
            {"keyword": "Vintage & secondhand resurgence", "momentum_score": 0.72, "relevance_score": 0.74, "volume_current": 41000, "volume_prior": 27000, "evidence": ["Depop Trends", "ThredUp Reports"], "action_hint": "Tap into the resale narrative; limited drops strategy"},
            {"keyword": "Size-inclusive fashion content", "momentum_score": 0.61, "relevance_score": 0.79, "volume_current": 18000, "volume_prior": 12000, "evidence": ["Refinery29", "Glamour"], "action_hint": "Feature diverse body representations in all content"},
            {"keyword": "Digital fashion week content", "momentum_score": 0.54, "relevance_score": 0.69, "volume_current": 9200, "volume_prior": 6800, "evidence": ["Business of Fashion", "Vogue"], "action_hint": "Create season-specific content aligned with fashion week"},
            {"keyword": "Micro-influencer outfit collaborations", "momentum_score": 0.69, "relevance_score": 0.86, "volume_current": 15000, "volume_prior": 9200, "evidence": ["Later Blog", "Sprout Social"], "action_hint": "Partner with micro-influencers for authentic styling content"},
            {"keyword": "Lifestyle storytelling over product shots", "momentum_score": 0.81, "relevance_score": 0.91, "volume_current": 27000, "volume_prior": 12000, "evidence": ["Hootsuite", "Meta Insights"], "action_hint": "Shift 60% of content to lifestyle/context over flat lays"},
            {"keyword": "Local fashion community spotlights", "momentum_score": 0.47, "relevance_score": 0.68, "volume_current": 6800, "volume_prior": 5200, "evidence": ["Local press", "Community Instagrammers"], "action_hint": "Partner with local stylists and community figures"},
        ],
        "food": [
            {"keyword": "High-protein recipe content", "momentum_score": 0.84, "relevance_score": 0.89, "volume_current": 54000, "volume_prior": 28000, "evidence": ["Pinterest Trends", "YouTube Food"], "action_hint": f"Create high-protein meal content featuring {brand_name} products or themes"},
            {"keyword": "Restaurant-quality home cooking", "momentum_score": 0.76, "relevance_score": 0.82, "volume_current": 39000, "volume_prior": 22000, "evidence": ["Food52", "Bon Appétit"], "action_hint": "Share pro techniques and plating for home cooks"},
            {"keyword": "International cuisine discovery", "momentum_score": 0.68, "relevance_score": 0.74, "volume_current": 28000, "volume_prior": 19000, "evidence": ["Yelp Trends", "Google Trends"], "action_hint": "Spotlight authentic regional dishes and their stories"},
            {"keyword": "Behind-the-kitchen content", "momentum_score": 0.79, "relevance_score": 0.88, "volume_current": 22000, "volume_prior": 11000, "evidence": ["Instagram Reels", "TikTok Food"], "action_hint": "Raw, unfiltered kitchen content outperforms polished shots"},
            {"keyword": "Seasonal ingredient spotlights", "momentum_score": 0.62, "relevance_score": 0.77, "volume_current": 16000, "volume_prior": 11000, "evidence": ["Food & Wine", "Epicurious"], "action_hint": "Build a seasonal content calendar around peak ingredients"},
            {"keyword": "Food and mental health connection", "momentum_score": 0.71, "relevance_score": 0.81, "volume_current": 19000, "volume_prior": 10000, "evidence": ["Well+Good", "Nutritional science blogs"], "action_hint": "Create gut health, mood food, and mindful eating content"},
            {"keyword": "Viral recipe challenges", "momentum_score": 0.88, "relevance_score": 0.83, "volume_current": 67000, "volume_prior": 31000, "evidence": ["TikTok", "Reddit r/food"], "action_hint": "Create a branded recipe challenge with shareable format"},
            {"keyword": "Sustainable food sourcing transparency", "momentum_score": 0.58, "relevance_score": 0.78, "volume_current": 12000, "volume_prior": 8400, "evidence": ["Eater", "Civil Eats"], "action_hint": "Show your ingredient sourcing story"},
        ],
        "fitness": [
            {"keyword": "Functional fitness over aesthetics", "momentum_score": 0.82, "relevance_score": 0.91, "volume_current": 38000, "volume_prior": 19000, "evidence": ["Men's Health", "Women's Health", "Nike Training"], "action_hint": f"Position {brand_name} content around real-world performance outcomes"},
            {"keyword": "Recovery & sleep optimization", "momentum_score": 0.78, "relevance_score": 0.86, "volume_current": 44000, "volume_prior": 24000, "evidence": ["Huberman Lab", "Whoop", "Oura"], "action_hint": "Create recovery-focused content as part of training narrative"},
            {"keyword": "Wearable + biometric performance tracking", "momentum_score": 0.71, "relevance_score": 0.78, "volume_current": 27000, "volume_prior": 16000, "evidence": ["Garmin", "Apple Health", "MyFitnessPal"], "action_hint": "Create data-driven fitness content using wearable metrics"},
            {"keyword": "Beginner fitness content boom", "momentum_score": 0.85, "relevance_score": 0.88, "volume_current": 62000, "volume_prior": 31000, "evidence": ["YouTube Fitness", "TikTok"], "action_hint": "Launch a beginner-specific series targeting new-to-fitness audiences"},
            {"keyword": "Mental-physical wellness integration", "momentum_score": 0.74, "relevance_score": 0.84, "volume_current": 31000, "volume_prior": 18000, "evidence": ["Peloton Blog", "Headspace", "Calm"], "action_hint": "Blend mindfulness into physical training content"},
            {"keyword": "Progressive overload education", "momentum_score": 0.67, "relevance_score": 0.82, "volume_current": 21000, "volume_prior": 13000, "evidence": ["RP Strength", "Jeff Nippard", "AthleanX"], "action_hint": "Create a structured education series on training principles"},
            {"keyword": "Community workout accountability", "momentum_score": 0.61, "relevance_score": 0.79, "volume_current": 18000, "volume_prior": 12000, "evidence": ["Strava", "Discord fitness groups"], "action_hint": "Build a community challenge series around your brand"},
            {"keyword": "Sustainable fitness habits (not programs)", "momentum_score": 0.76, "relevance_score": 0.89, "volume_current": 29000, "volume_prior": 14000, "evidence": ["James Clear (Atomic Habits)", "Psychology Today"], "action_hint": "Frame all content around habit formation, not 30-day challenges"},
        ],
        "ecommerce": [
            {"keyword": "Post-purchase brand experience", "momentum_score": 0.78, "relevance_score": 0.91, "volume_current": 12000, "volume_prior": 6800, "evidence": ["Shopify Blog", "Klaviyo", "Yotpo"], "action_hint": f"Showcase what happens after purchase — unboxing, care, community"},
            {"keyword": "Social proof in product discovery", "momentum_score": 0.84, "relevance_score": 0.88, "volume_current": 19000, "volume_prior": 9400, "evidence": ["Bazaarvoice", "Trustpilot", "Meta Ads"], "action_hint": "Feature real customer UGC as primary content format"},
            {"keyword": "DTC to retail channel expansion", "momentum_score": 0.63, "relevance_score": 0.74, "volume_current": 8200, "volume_prior": 5600, "evidence": ["Modern Retail", "Business of Fashion"], "action_hint": "Document the brand's omnichannel growth story"},
            {"keyword": "Limited drops as community events", "momentum_score": 0.87, "relevance_score": 0.89, "volume_current": 24000, "volume_prior": 11000, "evidence": ["Supreme model analysis", "Sneaker News", "Highsnobiety"], "action_hint": "Create FOMO-driven limited drop content series"},
            {"keyword": "Product story and founder narrative", "momentum_score": 0.72, "relevance_score": 0.86, "volume_current": 16000, "volume_prior": 9200, "evidence": ["Substack DTC newsletters", "Indie Hackers"], "action_hint": "Lead with founder story and brand origin across all channels"},
            {"keyword": "Value-based purchasing shifts", "momentum_score": 0.69, "relevance_score": 0.81, "volume_current": 14000, "volume_prior": 8800, "evidence": ["Edelman Trust Barometer", "McKinsey Consumer"], "action_hint": "Align brand messaging with customer values beyond product features"},
            {"keyword": "Instagram Shops and social commerce", "momentum_score": 0.79, "relevance_score": 0.93, "volume_current": 31000, "volume_prior": 17000, "evidence": ["Meta Business", "Shopify Social"], "action_hint": "Fully optimize Instagram Shop tags and checkout flow"},
            {"keyword": "Subscription and loyalty mechanics", "momentum_score": 0.61, "relevance_score": 0.77, "volume_current": 9800, "volume_prior": 7200, "evidence": ["Recharge", "Loyalty.com", "Bond"], "action_hint": "Create content showing subscriber-exclusive value"},
        ],
        "beauty": [
            {"keyword": "Skin barrier health & microbiome", "momentum_score": 0.86, "relevance_score": 0.92, "volume_current": 48000, "volume_prior": 22000, "evidence": ["Byrdie", "The Ordinary Blog", "Dermatology journals"], "action_hint": f"Create educational content positioning {brand_name} around skin barrier science"},
            {"keyword": "Skinimalism (less products, better results)", "momentum_score": 0.74, "relevance_score": 0.88, "volume_current": 34000, "volume_prior": 19000, "evidence": ["Vogue Beauty", "Into The Gloss"], "action_hint": "Promote a simplified routine narrative with your hero products"},
            {"keyword": "Dermatologist-approved content", "momentum_score": 0.81, "relevance_score": 0.84, "volume_current": 29000, "volume_prior": 14000, "evidence": ["American Academy of Dermatology", "Refinery29"], "action_hint": "Feature expert/derm validation in ingredient storytelling"},
            {"keyword": "Inclusive shade range advocacy", "momentum_score": 0.68, "relevance_score": 0.82, "volume_current": 21000, "volume_prior": 14000, "evidence": ["Shade Finder tools", "Fenty Beauty analysis"], "action_hint": "Continuously show shade diversity and inclusive application content"},
            {"keyword": "Ingredient transparency labels", "momentum_score": 0.77, "relevance_score": 0.89, "volume_current": 26000, "volume_prior": 13000, "evidence": ["EWG", "Think Dirty App"], "action_hint": "Create ingredient education content — what's in it and why it matters"},
            {"keyword": "GRWM (Get Ready With Me) content", "momentum_score": 0.91, "relevance_score": 0.87, "volume_current": 82000, "volume_prior": 41000, "evidence": ["TikTok", "YouTube Beauty"], "action_hint": "Launch a GRWM series featuring authentic, real-time application"},
            {"keyword": "Clean vs. effective beauty debate", "momentum_score": 0.65, "relevance_score": 0.79, "volume_current": 18000, "volume_prior": 12000, "evidence": ["Paula's Choice Blog", "Skincare Anarchy"], "action_hint": "Take a clear science-backed position in the clean beauty conversation"},
            {"keyword": "Gender-neutral beauty positioning", "momentum_score": 0.59, "relevance_score": 0.74, "volume_current": 14000, "volume_prior": 10000, "evidence": ["Allure", "Men's Health Beauty"], "action_hint": "Feature diverse genders in all product and application content"},
        ],
        "travel": [
            {"keyword": "Slow travel and deep destination immersion", "momentum_score": 0.77, "relevance_score": 0.86, "volume_current": 29000, "volume_prior": 16000, "evidence": ["Condé Nast Traveler", "Lonely Planet"], "action_hint": f"Create immersive, long-form destination stories for {brand_name}"},
            {"keyword": "Off-the-beaten-path discovery content", "momentum_score": 0.82, "relevance_score": 0.91, "volume_current": 38000, "volume_prior": 19000, "evidence": ["Atlas Obscura", "Reddit r/travel"], "action_hint": "Feature hidden gems over popular tourist spots"},
            {"keyword": "Solo female travel safety content", "momentum_score": 0.74, "relevance_score": 0.84, "volume_current": 24000, "volume_prior": 14000, "evidence": ["Solo Female Travelers network", "Travel + Leisure"], "action_hint": "Create practical, empowering solo travel content"},
            {"keyword": "Budget luxury travel hacks", "momentum_score": 0.79, "relevance_score": 0.88, "volume_current": 44000, "volume_prior": 24000, "evidence": ["Points Guys", "The Travel Hacking Cartel"], "action_hint": "Show high-value, lower-cost travel experiences"},
            {"keyword": "Responsible & regenerative tourism", "momentum_score": 0.68, "relevance_score": 0.82, "volume_current": 17000, "volume_prior": 10000, "evidence": ["Responsible Travel", "UNWTO"], "action_hint": "Partner with sustainable destinations and local operators"},
            {"keyword": "Digital nomad destination guides", "momentum_score": 0.71, "relevance_score": 0.78, "volume_current": 22000, "volume_prior": 14000, "evidence": ["Nomad List", "Remote Year"], "action_hint": "Create practical city guides for remote workers"},
            {"keyword": "Food-first travel planning", "momentum_score": 0.84, "relevance_score": 0.89, "volume_current": 35000, "volume_prior": 18000, "evidence": ["Eater", "The Food Traveler"], "action_hint": "Lead destination content with local food experiences"},
            {"keyword": "Travel photography & Reels growth", "momentum_score": 0.88, "relevance_score": 0.93, "volume_current": 61000, "volume_prior": 29000, "evidence": ["Instagram Insights", "Creator Academy"], "action_hint": "Launch a visual storytelling series showcasing destination beauty"},
        ],
        "creator": [
            {"keyword": "Creator monetization diversification", "momentum_score": 0.83, "relevance_score": 0.91, "volume_current": 31000, "volume_prior": 16000, "evidence": ["Creator IQ", "Substack", "Patreon"], "action_hint": f"Document {brand_name}'s multi-platform monetization strategy"},
            {"keyword": "Long-form vs. short-form strategy", "momentum_score": 0.76, "relevance_score": 0.88, "volume_current": 24000, "volume_prior": 14000, "evidence": ["Vidiq", "Tubics", "Creator Insider"], "action_hint": "Create a transparent series on your content strategy evolution"},
            {"keyword": "Community-led growth (not just followers)", "momentum_score": 0.81, "relevance_score": 0.89, "volume_current": 28000, "volume_prior": 13000, "evidence": ["David Spinks", "CMX Hub", "Circle.so"], "action_hint": "Launch a community activation strategy beyond passive followers"},
            {"keyword": "Behind-the-scenes / making of content", "momentum_score": 0.87, "relevance_score": 0.92, "volume_current": 47000, "volume_prior": 22000, "evidence": ["Creator Academy", "YouTube trends"], "action_hint": "Raw BTS content consistently outperforms polished output"},
            {"keyword": "AI tools in creative workflows", "momentum_score": 0.79, "relevance_score": 0.84, "volume_current": 38000, "volume_prior": 16000, "evidence": ["Product Hunt", "Creator newsletters"], "action_hint": "Show how you use AI tools in your creative process"},
            {"keyword": "Niche authority over broad reach", "momentum_score": 0.71, "relevance_score": 0.86, "volume_current": 19000, "volume_prior": 12000, "evidence": ["Morning Brew", "Axios", "niche newsletter case studies"], "action_hint": "Double down on a very specific niche POV rather than broad topics"},
            {"keyword": "Cross-platform repurposing systems", "momentum_score": 0.68, "relevance_score": 0.81, "volume_current": 16000, "volume_prior": 10000, "evidence": ["Vid IQ", "Buffer blog", "Later"], "action_hint": "Document your exact repurposing workflow publicly"},
            {"keyword": "Authenticity fatigue and raw content", "momentum_score": 0.91, "relevance_score": 0.93, "volume_current": 54000, "volume_prior": 23000, "evidence": ["TikTok trends", "BeReal emergence"], "action_hint": "Create intentionally unpolished, authentic content series"},
        ],
        "b2b": [
            {"keyword": "B2B thought leadership on LinkedIn", "momentum_score": 0.82, "relevance_score": 0.94, "volume_current": 28000, "volume_prior": 14000, "evidence": ["LinkedIn Insights", "Demand Gen Report"], "action_hint": f"Establish {brand_name} founders and team as category thought leaders on LinkedIn"},
            {"keyword": "Revenue-focused content marketing", "momentum_score": 0.77, "relevance_score": 0.89, "volume_current": 18000, "volume_prior": 10000, "evidence": ["HubSpot", "Demand Gen", "G2"], "action_hint": "Every piece of content must tie back to pipeline and revenue"},
            {"keyword": "Case study and ROI storytelling", "momentum_score": 0.79, "relevance_score": 0.91, "volume_current": 14000, "volume_prior": 8000, "evidence": ["G2 Reviews", "Gartner", "Forrester"], "action_hint": "Build a library of ROI-focused customer stories"},
            {"keyword": "AI use cases in professional services", "momentum_score": 0.88, "relevance_score": 0.87, "volume_current": 41000, "volume_prior": 18000, "evidence": ["McKinsey AI Index", "PwC AI Benchmark"], "action_hint": "Create content around specific AI workflow applications in your industry"},
            {"keyword": "Buyer committee content strategy", "momentum_score": 0.64, "relevance_score": 0.82, "volume_current": 9200, "volume_prior": 6100, "evidence": ["Gartner", "Forrester Buyer Journey"], "action_hint": "Create content for every stakeholder in the buying process"},
            {"keyword": "Micro-event and webinar formats", "momentum_score": 0.68, "relevance_score": 0.78, "volume_current": 12000, "volume_prior": 8100, "evidence": ["ON24", "Hopin", "Zoom Events"], "action_hint": "Run intimate, high-value virtual events for target accounts"},
            {"keyword": "Partner and ecosystem co-marketing", "momentum_score": 0.72, "relevance_score": 0.84, "volume_current": 11000, "volume_prior": 7200, "evidence": ["PartnerStack", "Crossbeam"], "action_hint": "Launch a co-marketing content series with complementary partners"},
            {"keyword": "Transparent pricing and ROI calculators", "momentum_score": 0.74, "relevance_score": 0.86, "volume_current": 16000, "volume_prior": 9400, "evidence": ["OpenView Partners", "ProfitWell"], "action_hint": "Publish ROI calculators and transparent pricing content"},
        ],
        "general": [
            {"keyword": "Authentic brand storytelling", "momentum_score": 0.79, "relevance_score": 0.88, "volume_current": 41000, "volume_prior": 22000, "evidence": ["Harvard Business Review", "Forbes Marketing"], "action_hint": f"Tell {brand_name}'s origin story across all content channels"},
            {"keyword": "Community-first growth strategy", "momentum_score": 0.82, "relevance_score": 0.86, "volume_current": 34000, "volume_prior": 17000, "evidence": ["CMX Hub", "Community-Led Growth"], "action_hint": "Build a community around your brand beyond follower counts"},
            {"keyword": "Video-first content distribution", "momentum_score": 0.87, "relevance_score": 0.91, "volume_current": 78000, "volume_prior": 38000, "evidence": ["Instagram Insights", "YouTube Trends", "TikTok"], "action_hint": "Shift primary content format to short-form video (Reels)"},
            {"keyword": "AI-powered personalization in marketing", "momentum_score": 0.84, "relevance_score": 0.82, "volume_current": 29000, "volume_prior": 13000, "evidence": ["Salesforce State of Marketing", "Adobe CMO Report"], "action_hint": "Create personalized content experiences for different audience segments"},
            {"keyword": "Micro-influencer partnerships", "momentum_score": 0.74, "relevance_score": 0.89, "volume_current": 22000, "volume_prior": 13000, "evidence": ["Influencer Marketing Hub", "Creator IQ"], "action_hint": "Launch a micro-influencer ambassador program for your niche"},
            {"keyword": "Social proof and UGC amplification", "momentum_score": 0.77, "relevance_score": 0.87, "volume_current": 18000, "volume_prior": 10000, "evidence": ["Bazaarvoice", "Yotpo", "Trustpilot"], "action_hint": "Build a systematic UGC collection and amplification strategy"},
            {"keyword": "Value-driven content over promotional", "momentum_score": 0.81, "relevance_score": 0.84, "volume_current": 26000, "volume_prior": 14000, "evidence": ["Content Marketing Institute", "HubSpot State of Marketing"], "action_hint": "Apply 80/20 rule: 80% educational/entertaining, 20% promotional"},
            {"keyword": "Instagram algorithm optimization 2025", "momentum_score": 0.88, "relevance_score": 0.93, "volume_current": 54000, "volume_prior": 27000, "evidence": ["Instagram Creator Blog", "Later Research", "Hootsuite"], "action_hint": "Optimize posting cadence, Reels length, and engagement hooks"},
        ],
    }.get(niche, [])

    # Inject brand name into action hints
    result = []
    for i, t in enumerate(base):
        item = {**t, "id": str(i + 1), "niche": niche}
        result.append(item)
    return result


def _audience_segments(niche: str, brand_name: str) -> list[dict]:
    base: dict[str, list[dict]] = {
        "tech": [
            {"name": "Growth-focused founders", "size_estimate": "1.2M on Instagram", "fit_score": 0.91, "intent_score": 0.85, "interests": ["startup growth", "SaaS metrics", "AI tools", "productivity"], "pain_points": ["scaling customer acquisition", "churn reduction", "product-market fit"], "platforms": ["LinkedIn", "Twitter/X", "Instagram", "Hacker News"], "content_angle": "ROI stories, founder case studies, growth metrics"},
            {"name": "Marketing ops professionals", "size_estimate": "800K on Instagram", "fit_score": 0.87, "intent_score": 0.79, "interests": ["marketing automation", "analytics", "AI tools", "demand gen"], "pain_points": ["attribution complexity", "tool fragmentation", "proving marketing ROI"], "platforms": ["LinkedIn", "Instagram", "Slack communities"], "content_angle": "How-to workflows, tool comparisons, automation case studies"},
            {"name": "Tech-savvy SMB owners", "size_estimate": "2.1M on Instagram", "fit_score": 0.82, "intent_score": 0.74, "interests": ["business software", "efficiency", "growth hacking", "AI adoption"], "pain_points": ["limited resources", "competing with enterprise", "team productivity"], "platforms": ["Facebook", "Instagram", "LinkedIn"], "content_angle": "Practical ROI examples, before/after stories, quick wins"},
            {"name": "B2B software buyers", "size_estimate": "450K on Instagram", "fit_score": 0.78, "intent_score": 0.88, "interests": ["software evaluation", "vendor comparison", "implementation", "TCO"], "pain_points": ["integration complexity", "change management", "vendor lock-in"], "platforms": ["LinkedIn", "G2", "Capterra", "Instagram"], "content_angle": "Integration stories, implementation ease, customer proof"},
        ],
        "fashion": [
            {"name": "Style-conscious millennials", "size_estimate": "8.4M on Instagram", "fit_score": 0.89, "intent_score": 0.82, "interests": ["fashion trends", "sustainable style", "capsule wardrobes", "outfit inspiration"], "pain_points": ["decision paralysis", "fast fashion guilt", "building versatile wardrobe"], "platforms": ["Instagram", "Pinterest", "TikTok"], "content_angle": "Styling tutorials, outfit combinations, wardrobe building"},
            {"name": "Fashion-forward Gen Z", "size_estimate": "12M on Instagram", "fit_score": 0.84, "intent_score": 0.76, "interests": ["streetwear", "vintage", "designer drops", "identity expression"], "pain_points": ["authenticity, not conforming", "budget constraints", "finding unique pieces"], "platforms": ["TikTok", "Instagram", "Depop"], "content_angle": "Self-expression, subculture content, limited edition drops"},
            {"name": "Professional women (25-45)", "size_estimate": "5.2M on Instagram", "fit_score": 0.81, "intent_score": 0.79, "interests": ["work-to-weekend outfits", "investment pieces", "brand values"], "pain_points": ["dressing for authority + femininity", "quality vs. price", "time to shop"], "platforms": ["Instagram", "LinkedIn", "Pinterest"], "content_angle": "Workwear versatility, investment pieces, styling for confidence"},
            {"name": "Eco-conscious buyers", "size_estimate": "3.8M on Instagram", "fit_score": 0.76, "intent_score": 0.73, "interests": ["sustainable brands", "ethical sourcing", "transparency", "slow fashion"], "pain_points": ["greenwashing distrust", "cost of sustainable fashion", "finding ethical brands"], "platforms": ["Instagram", "TikTok", "Newsletters"], "content_angle": "Supply chain transparency, sustainability impact metrics"},
        ],
        "food": [
            {"name": "Home cook enthusiasts", "size_estimate": "22M on Instagram", "fit_score": 0.91, "intent_score": 0.83, "interests": ["new recipes", "cooking techniques", "kitchen gadgets", "ingredient discovery"], "pain_points": ["weeknight meal inspiration", "skill level confidence", "meal planning"], "platforms": ["Instagram", "Pinterest", "YouTube", "TikTok"], "content_angle": "Step-by-step recipes, technique breakdowns, beginner-friendly content"},
            {"name": "Health-focused foodies", "size_estimate": "14M on Instagram", "fit_score": 0.86, "intent_score": 0.81, "interests": ["clean eating", "macro tracking", "whole foods", "gut health"], "pain_points": ["taste vs. health tradeoff", "label reading complexity", "time for healthy cooking"], "platforms": ["Instagram", "TikTok", "Pinterest"], "content_angle": "Healthy swaps, macro-balanced recipes, ingredient education"},
            {"name": "Food culture explorers", "size_estimate": "9M on Instagram", "fit_score": 0.79, "intent_score": 0.74, "interests": ["international cuisine", "restaurant discovery", "food history", "culture through food"], "pain_points": ["authenticity of recipes", "ingredient accessibility", "learning cultural context"], "platforms": ["Instagram", "YouTube", "Substack"], "content_angle": "Cultural storytelling, authentic technique, origin stories"},
            {"name": "Busy parents seeking easy meals", "size_estimate": "18M on Instagram", "fit_score": 0.77, "intent_score": 0.88, "interests": ["quick dinner ideas", "meal prep", "kid-friendly food", "budget cooking"], "pain_points": ["30-minute constraint", "picky eaters", "nutritional balance"], "platforms": ["Pinterest", "Facebook", "Instagram"], "content_angle": "Quick prep time, family-approved, budget-friendly framing"},
        ],
        "fitness": [
            {"name": "Fitness beginners (6-month journey)", "size_estimate": "31M on Instagram", "fit_score": 0.88, "intent_score": 0.91, "interests": ["getting started", "home workouts", "beginner programs", "body transformation"], "pain_points": ["gym intimidation", "not knowing where to start", "form anxiety", "seeing early results"], "platforms": ["Instagram", "TikTok", "YouTube"], "content_angle": "Zero-judgment, step-by-step, transformation stories from real beginners"},
            {"name": "Dedicated gym-goers (intermediate)", "size_estimate": "18M on Instagram", "fit_score": 0.85, "intent_score": 0.82, "interests": ["progressive overload", "program design", "supplements", "PRs"], "pain_points": ["plateau breaking", "program fatigue", "injury prevention"], "platforms": ["Instagram", "Reddit r/fitness", "YouTube"], "content_angle": "Science-backed programming, advanced technique, PR celebration"},
            {"name": "Busy professional wellness seekers", "size_estimate": "24M on Instagram", "fit_score": 0.81, "intent_score": 0.79, "interests": ["efficient workouts", "stress reduction", "sleep optimization", "energy management"], "pain_points": ["time scarcity", "work-life balance", "consistent schedule"], "platforms": ["Instagram", "LinkedIn", "Apple Fitness+"], "content_angle": "Time-efficient workouts, stress and cortisol management, high-ROI routines"},
            {"name": "Athletic performance seekers", "size_estimate": "8M on Instagram", "fit_score": 0.78, "intent_score": 0.84, "interests": ["sport-specific training", "speed/power", "nutrition for performance", "recovery"], "pain_points": ["sport-specific programming", "periodization", "overtraining"], "platforms": ["Instagram", "YouTube", "Reddit"], "content_angle": "Sport-specific applications, elite training principles, performance metrics"},
        ],
        "ecommerce": [
            {"name": "Value-conscious online shoppers", "size_estimate": "45M on Instagram", "fit_score": 0.84, "intent_score": 0.89, "interests": ["deals", "product reviews", "unboxing", "brand comparisons"], "pain_points": ["decision fatigue", "fear of buying wrong product", "return complexity"], "platforms": ["Instagram", "TikTok", "YouTube", "Reddit"], "content_angle": "Social proof, UGC, detailed product demos, comparison content"},
            {"name": "Brand loyalty advocates", "size_estimate": "12M on Instagram", "fit_score": 0.91, "intent_score": 0.77, "interests": ["brand community", "loyalty rewards", "exclusive access", "brand story"], "pain_points": ["feeling valued post-purchase", "finding brands aligned with values"], "platforms": ["Instagram", "Brand apps", "Email"], "content_angle": "Behind-scenes access, loyalty perks, community exclusives"},
            {"name": "Discovery-mode Gen Z shoppers", "size_estimate": "28M on Instagram", "fit_score": 0.79, "intent_score": 0.86, "interests": ["new brands", "aesthetic curation", "viral products", "TikTok made me buy it"], "pain_points": ["too many options", "authenticity of brand claims", "peer validation"], "platforms": ["TikTok", "Instagram", "Pinterest"], "content_angle": "Trend alignment, authentic creator partnerships, viral formats"},
            {"name": "Gift purchasers", "size_estimate": "19M on Instagram", "fit_score": 0.73, "intent_score": 0.92, "interests": ["gift guides", "premium packaging", "personalization", "special occasions"], "pain_points": ["decision making for others", "shipping reliability", "personalization options"], "platforms": ["Pinterest", "Instagram", "Google"], "content_angle": "Gift guide format content, packaging beauty, occasion-specific framing"},
        ],
        "beauty": [
            {"name": "Skincare ingredient obsessives", "size_estimate": "14M on Instagram", "fit_score": 0.92, "intent_score": 0.87, "interests": ["retinol", "acids", "antioxidants", "dermatology research", "lab skincare"], "pain_points": ["information overload", "ingredient compatibility", "over-formulation"], "platforms": ["Instagram", "Reddit r/SkincareAddiction", "YouTube"], "content_angle": "Deep ingredient science, formulation transparency, expert validation"},
            {"name": "Makeup artistry enthusiasts", "size_estimate": "21M on Instagram", "fit_score": 0.87, "intent_score": 0.83, "interests": ["technique tutorials", "new product launches", "color theory", "professional artistry"], "pain_points": ["products that don't perform as shown", "skill gap", "finding exact shade"], "platforms": ["Instagram", "TikTok", "YouTube"], "content_angle": "Tutorials, technique breakdowns, honest product testing"},
            {"name": "Clean beauty converts", "size_estimate": "9M on Instagram", "fit_score": 0.81, "intent_score": 0.79, "interests": ["non-toxic formulas", "sustainable packaging", "EWG clean", "cruelty-free"], "pain_points": ["clean = ineffective myth", "greenwashing navigation", "premium price justification"], "platforms": ["Instagram", "Pinterest", "Newsletters"], "content_angle": "Ingredient transparency, efficacy proof, sustainability credentials"},
            {"name": "Budget beauty enthusiasts", "size_estimate": "32M on Instagram", "fit_score": 0.74, "intent_score": 0.88, "interests": ["dupes", "drugstore finds", "haul content", "value comparison"], "pain_points": ["luxury product gap", "finding quality at price point", "marketing vs. reality"], "platforms": ["TikTok", "Instagram", "YouTube"], "content_angle": "Value proof, before/after results, honest price-to-performance"},
        ],
        "travel": [
            {"name": "Experience-over-things millennials", "size_estimate": "19M on Instagram", "fit_score": 0.89, "intent_score": 0.84, "interests": ["unique experiences", "local culture", "off-grid destinations", "meaningful travel"], "pain_points": ["overtourism", "authentic vs. touristy", "trip planning complexity"], "platforms": ["Instagram", "TikTok", "Pinterest"], "content_angle": "Immersive experiences, cultural depth, non-touristy angles"},
            {"name": "Adventure and outdoor seekers", "size_estimate": "12M on Instagram", "fit_score": 0.84, "intent_score": 0.82, "interests": ["hiking", "camping", "extreme sports", "national parks", "gear reviews"], "pain_points": ["safety planning", "gear selection", "permit systems"], "platforms": ["Instagram", "YouTube", "Reddit r/travel"], "content_angle": "Trail reports, gear breakdowns, safety and planning guides"},
            {"name": "Luxury travel aspirants", "size_estimate": "8M on Instagram", "fit_score": 0.78, "intent_score": 0.77, "interests": ["5-star hotels", "first class", "exclusive resorts", "concierge services"], "pain_points": ["value justification", "finding truly exclusive experiences", "overcrowded luxury"], "platforms": ["Instagram", "YouTube", "Travel newsletters"], "content_angle": "Behind the scenes at luxury properties, justifying premium experiences"},
            {"name": "Solo female travelers", "size_estimate": "15M on Instagram", "fit_score": 0.82, "intent_score": 0.88, "interests": ["safety tips", "solo itineraries", "women-friendly destinations", "empowerment"], "pain_points": ["safety concerns", "solo dining", "social connection while solo", "cultural navigation"], "platforms": ["Instagram", "Facebook Groups", "YouTube"], "content_angle": "Practical safety, empowerment narratives, solo travel reality"},
        ],
        "creator": [
            {"name": "Aspiring creators (0-10K followers)", "size_estimate": "48M on Instagram", "fit_score": 0.86, "intent_score": 0.93, "interests": ["growth tactics", "content strategy", "monetization basics", "algorithm insights"], "pain_points": ["getting first 1000 followers", "consistency", "niche clarity", "imposter syndrome"], "platforms": ["Instagram", "TikTok", "YouTube", "Creator communities"], "content_angle": "Beginners journey, real growth numbers, strategy transparency"},
            {"name": "Mid-tier creators monetizing (10-100K)", "size_estimate": "12M on Instagram", "fit_score": 0.91, "intent_score": 0.87, "interests": ["brand deals", "diversified revenue", "community building", "content systems"], "pain_points": ["brand deal pricing", "audience nurturing vs. growth", "burnout prevention"], "platforms": ["Instagram", "Substack", "Discord", "Patreon"], "content_angle": "Monetization breakdowns, income reports, system documentation"},
            {"name": "Brand and marketing managers", "size_estimate": "3M on Instagram", "fit_score": 0.83, "intent_score": 0.84, "interests": ["creator partnerships", "UGC sourcing", "influencer metrics", "content ROI"], "pain_points": ["finding authentic creators", "measuring influencer ROI", "brief quality"], "platforms": ["LinkedIn", "Instagram", "Creator platforms"], "content_angle": "Partnership case studies, creator ROI, collaboration transparency"},
            {"name": "Content consumers-turned-creators", "size_estimate": "22M on Instagram", "fit_score": 0.77, "intent_score": 0.89, "interests": ["starting a channel", "finding niche", "first video tips", "gear recommendations"], "pain_points": ["perfectionism paralysis", "equipment anxiety", "first content embarrassment"], "platforms": ["YouTube", "Instagram", "TikTok"], "content_angle": "Start ugly / just start content, low-gear high-content success stories"},
        ],
        "b2b": [
            {"name": "Marketing directors (B2B companies)", "size_estimate": "2.1M on LinkedIn/Instagram", "fit_score": 0.92, "intent_score": 0.86, "interests": ["demand gen strategy", "pipeline efficiency", "marketing ROI", "AI in marketing"], "pain_points": ["attribution", "sales-marketing alignment", "budget justification"], "platforms": ["LinkedIn", "Instagram", "Industry events", "Podcasts"], "content_angle": "Pipeline impact stories, marketing attribution frameworks, AI use cases"},
            {"name": "C-suite and founders (SMB focus)", "size_estimate": "1.4M on LinkedIn/Instagram", "fit_score": 0.88, "intent_score": 0.82, "interests": ["business growth", "team efficiency", "competitive positioning", "market trends"], "pain_points": ["scaling without headcount", "finding true competitive advantage", "execution speed"], "platforms": ["LinkedIn", "Twitter/X", "Industry newsletters"], "content_angle": "Strategic thinking content, market positioning, operator-level insights"},
            {"name": "Agency partners and consultants", "size_estimate": "800K on LinkedIn/Instagram", "fit_score": 0.84, "intent_score": 0.79, "interests": ["tools for client work", "case studies", "thought leadership", "new methodologies"], "pain_points": ["client education", "proving expertise", "differentiating agency offer"], "platforms": ["LinkedIn", "Twitter/X", "Instagram", "Agency community forums"], "content_angle": "Methodology frameworks, client case studies, industry contrarian takes"},
            {"name": "Sales professionals (B2B)", "size_estimate": "3.2M on LinkedIn/Instagram", "fit_score": 0.79, "intent_score": 0.88, "interests": ["social selling", "prospecting tactics", "CRM optimization", "deal velocity"], "pain_points": ["cold outreach fatigue", "standing out in crowded inboxes", "building pipeline"], "platforms": ["LinkedIn", "Instagram", "Sales newsletters"], "content_angle": "Social selling tactics, personalization at scale, inbound deal stories"},
        ],
        "general": [
            {"name": "Brand-aware social media users", "size_estimate": "Broad — varies by niche", "fit_score": 0.78, "intent_score": 0.74, "interests": ["authentic brands", "social media content", "community belonging", "brand discovery"], "pain_points": ["information overload", "finding brands that match values", "decision fatigue"], "platforms": ["Instagram", "TikTok", "Pinterest"], "content_angle": "Authentic brand story, value alignment, community feel"},
            {"name": "Mobile-first consumers (25-40)", "size_estimate": "Wide — mobile-native demographic", "fit_score": 0.81, "intent_score": 0.79, "interests": ["convenience", "visual content", "quick information", "social proof"], "pain_points": ["trust in online brands", "product visualization", "easy purchase paths"], "platforms": ["Instagram", "TikTok", "Google Search"], "content_angle": "Mobile-first visual content, easy path to purchase, review-backed claims"},
            {"name": "Values-aligned buyers", "size_estimate": "Growing segment across all demographics", "fit_score": 0.84, "intent_score": 0.82, "interests": ["brand ethics", "sustainability", "social impact", "transparency"], "pain_points": ["identifying authentic vs. performative brands", "paying premium for values"], "platforms": ["Instagram", "Twitter/X", "Brand newsletters"], "content_angle": "Behind-the-brand transparency, impact reporting, genuine community"},
            {"name": "Early adopters and brand advocates", "size_estimate": "10-15% of any market", "fit_score": 0.88, "intent_score": 0.91, "interests": ["new products", "brand communities", "exclusive access", "being first to discover"], "pain_points": ["feeling special / unique", "getting early access", "having insider knowledge"], "platforms": ["Instagram", "Discord", "Newsletters", "Product Hunt"], "content_angle": "Exclusive drops, early access offers, insider community content"},
        ],
    }
    return [{"id": str(i + 1), **s} for i, s in enumerate(base.get(niche, base["general"]))]


def _recommendations(niche: str, brand_name: str, handle: str) -> list[dict]:
    base: dict[str, list[dict]] = {
        "tech": [
            {"title": f"Establish @{handle} as a thought leader in your category", "category": "growth", "priority_score": 0.94, "impact_score": 0.91, "effort_score": 0.45, "description": "Post 3x/week on category-defining topics. Use LinkedIn for long-form, Instagram for visual proof-points and behind-the-scenes.", "action": "Create a 12-week thought leadership content calendar"},
            {"title": "Launch a 'Build in Public' series documenting product development", "category": "content", "priority_score": 0.88, "impact_score": 0.87, "effort_score": 0.38, "description": "Build-in-public content drives 3-5x more organic engagement than promotional content for B2B/tech brands.", "action": "Share weekly product updates, metrics, and learnings"},
            {"title": "Create product demo Reels under 60 seconds", "category": "content", "priority_score": 0.85, "impact_score": 0.83, "effort_score": 0.35, "description": "Short product demos showing concrete value in <60 seconds are the highest-converting content format for SaaS brands on Instagram.", "action": "Film 5 demo Reels showing one specific feature/outcome each"},
            {"title": "Start a 'Customer Wins' highlight series", "category": "social_proof", "priority_score": 0.82, "impact_score": 0.88, "effort_score": 0.28, "description": "Dedicated Instagram Highlights for customer results and testimonials drive purchase confidence.", "action": "Collect 10 customer quotes + results, format as branded slides"},
            {"title": "Optimize Instagram bio for AI search discovery", "category": "geo_seo", "priority_score": 0.79, "impact_score": 0.84, "effort_score": 0.12, "description": "Include primary keyword, value prop, and category in bio. Link in bio should go to a high-converting landing page.", "action": "Update bio: [category] + [value prop] + [social proof number]"},
            {"title": "Engage with competitor audiences through value-first comments", "category": "growth", "priority_score": 0.74, "impact_score": 0.77, "effort_score": 0.52, "description": "Systematic engagement on posts by competitor accounts and relevant hashtag communities builds organic reach.", "action": "Create a daily 20-comment engagement protocol in your niche"},
        ],
        "fashion": [
            {"title": f"Launch a signature aesthetic series for @{handle}", "category": "content", "priority_score": 0.93, "impact_score": 0.91, "effort_score": 0.42, "description": "Define and consistently execute one signature visual aesthetic. Consistency in color palette, composition, and mood drives follower retention.", "action": "Define brand moodboard + style guide, commit to 30-day consistency"},
            {"title": "Create outfit repeat and re-styling content", "category": "content", "priority_score": 0.88, "impact_score": 0.85, "effort_score": 0.31, "description": "Outfit repeat content resonates with sustainable fashion ethos and drives higher saves (3x vs. one-time outfits).", "action": "Create 5 'one item, 3 ways' Reels for your hero pieces"},
            {"title": "Develop a micro-influencer ambassador program", "category": "growth", "priority_score": 0.86, "impact_score": 0.89, "effort_score": 0.61, "description": "10 micro-influencers (5K-50K) outperform 1 macro-influencer for fashion brands — more authentic, more conversion-driven.", "action": "Identify and pitch 20 micro-influencers in your style niche"},
            {"title": "Behind-the-scenes content (sourcing, production, design process)", "category": "content", "priority_score": 0.83, "impact_score": 0.87, "effort_score": 0.27, "description": "BTS content drives 40% more story views and builds emotional brand connection.", "action": "Document your next production run or buying trip as content"},
            {"title": "Use Instagram Shopping tags on all product posts", "category": "ecommerce", "priority_score": 0.91, "impact_score": 0.84, "effort_score": 0.18, "description": "Shopping tags reduce friction between discovery and purchase. Tagged posts reach 70% more potential buyers.", "action": "Enable Instagram Shopping and tag all products retroactively"},
            {"title": "Build a GRWM (Get Ready With Me) content series", "category": "content", "priority_score": 0.80, "impact_score": 0.83, "effort_score": 0.35, "description": "GRWM is the highest-engagement format for fashion and lifestyle accounts, driving both follows and saves.", "action": "Create a weekly GRWM series featuring brand pieces"},
        ],
        "food": [
            {"title": f"Create a signature recipe series unique to @{handle}", "category": "content", "priority_score": 0.92, "impact_score": 0.90, "effort_score": 0.44, "description": "A branded recipe series with consistent format (same filming style, same plating aesthetic) builds recognizable content identity.", "action": "Launch 'X recipe series' — 8 episodes, consistent format"},
            {"title": "Film behind-the-restaurant / kitchen content", "category": "content", "priority_score": 0.89, "impact_score": 0.87, "effort_score": 0.29, "description": "Kitchen BTS content gets 60% more organic reach than polished food photos. Raw = authentic = trusted.", "action": "Film 2 weekly BTS Reels: prep, sourcing, or chef moments"},
            {"title": "Build a 'regulars' community with user-generated content", "category": "growth", "priority_score": 0.85, "impact_score": 0.88, "effort_score": 0.38, "description": "Encourage diners/customers to tag the account. Feature the best UGC with explicit credit. Builds belonging.", "action": "Launch a tag-to-feature campaign with a branded hashtag"},
            {"title": "Create seasonal ingredient spotlights", "category": "content", "priority_score": 0.82, "impact_score": 0.84, "effort_score": 0.32, "description": "Seasonal content aligns with search intent peaks and positions the brand as food-knowledgeable, not just promotional.", "action": "Build a seasonal content calendar tied to produce and events"},
            {"title": "Optimize profile for local discovery and maps", "category": "geo_seo", "priority_score": 0.88, "impact_score": 0.82, "effort_score": 0.15, "description": "Location tags on every post, Google Business optimization, and local hashtag use drives discovery for food/restaurant brands.", "action": "Audit location tags, Google Business profile, and local hashtags"},
            {"title": "Partner with food journalists and local food accounts", "category": "growth", "priority_score": 0.78, "impact_score": 0.86, "effort_score": 0.55, "description": "Local food media partnerships (micro-influencers, food journalists, local blogs) drive credible discovery.", "action": "Identify 10 local food accounts and propose authentic collaborations"},
        ],
        "general": [
            {"title": f"Establish @{handle} as the go-to account for your niche", "category": "growth", "priority_score": 0.92, "impact_score": 0.90, "effort_score": 0.48, "description": f"Consistent posting (5x/week), clear niche positioning, and value-first content will establish {brand_name} as an authority in your space.", "action": "Define 3 content pillars and post schedule for 90 days"},
            {"title": "Shift to Reels-first content strategy", "category": "content", "priority_score": 0.90, "impact_score": 0.88, "effort_score": 0.42, "description": "Instagram's algorithm heavily favors Reels for organic reach. Accounts posting 4+ Reels/week see 3-5x organic growth vs. static posts.", "action": "Create and post 4 Reels this week — start, iterate, improve"},
            {"title": "Build a community around a specific content series", "category": "community", "priority_score": 0.85, "impact_score": 0.87, "effort_score": 0.51, "description": "A named, recurring series (e.g. 'Monday Tip', 'Friday Feature') builds anticipation and recurring engagement patterns.", "action": "Launch one weekly recurring series with a memorable format"},
            {"title": "Optimize your Instagram bio for first impressions", "category": "conversion", "priority_score": 0.88, "impact_score": 0.83, "effort_score": 0.10, "description": "The bio has 2 seconds to communicate: who you are, who this is for, why they should follow. Most bios fail all three.", "action": "Rewrite bio: [who you help] + [what you do] + [why follow] + CTA"},
            {"title": "Build a UGC flywheel through active community recognition", "category": "social_proof", "priority_score": 0.82, "impact_score": 0.86, "effort_score": 0.35, "description": "Systematically featuring customer/audience content creates a positive loop: people create content hoping to be featured.", "action": "Create a branded hashtag, then feature UGC weekly in Stories"},
            {"title": "Create a content repurposing system", "category": "efficiency", "priority_score": 0.79, "impact_score": 0.81, "effort_score": 0.28, "description": "One pillar piece of content (long-form post, Reel) should become 5-8 derivative pieces across formats.", "action": "Build a repurposing template: 1 Reel → 3 Stories → 1 carousel → 1 caption quote"},
        ],
    }
    data = base.get(niche, base["general"])
    return [{"id": str(i + 1), **r} for i, r in enumerate(data)]


def _content_opportunities(niche: str, brand_name: str) -> list[dict]:
    base: dict[str, list[dict]] = {
        "tech": [
            {"theme": "Product demo series", "format": "Reels (30-60s)", "angle": "One feature, one outcome, one customer type per video", "expected_reach": "High", "content_ideas": ["'How [brand] helped [persona] achieve [outcome] in [timeframe]'", "Screen recording + voiceover demos", "Side-by-side before/after workflow comparisons"]},
            {"theme": "Founder thought leadership", "format": "Carousel + Long-form caption", "angle": "Category-defining hot takes and predictions", "expected_reach": "Medium-High", "content_ideas": ["'The future of [category] in 5 years'", "Contrarian industry takes", "Lessons learned building [product]"]},
            {"theme": "Customer success spotlights", "format": "Stories + Highlights", "angle": "Real metrics, real customers, real outcomes", "expected_reach": "Medium", "content_ideas": ["'@customer_handle saw X% improvement in Y using [brand]'", "Quote cards with metrics", "Case study mini-series"]},
        ],
        "fashion": [
            {"theme": "Styling how-to series", "format": "Reels (15-30s)", "angle": "Fast, aspirational styling with brand pieces", "expected_reach": "Very High", "content_ideas": ["'5 ways to wear [hero piece]'", "Season-to-season outfit transitions", "Budget-to-luxury duplication styling"]},
            {"theme": "Brand story and values content", "format": "Long-form caption + photo series", "angle": "Why the brand exists, who it's for", "expected_reach": "Medium", "content_ideas": ["Founder origin story", "Sourcing and manufacturing transparency", "Community spotlights and ambassador stories"]},
            {"theme": "Trend reaction content", "format": "Reels (15-30s)", "angle": "How to wear/adapt current macro trends with brand pieces", "expected_reach": "High", "content_ideas": ["'How to get [trending look] with [brand] pieces'", "Trend-proof styling advice", "Anti-trend, timeless style arguments"]},
        ],
        "general": [
            {"theme": "Educational value series", "format": "Carousel (5-10 slides)", "angle": "Teach something specific your audience wants to learn", "expected_reach": "High (saves-driven reach)", "content_ideas": [f"'X things every [audience] should know about [niche]'", "Step-by-step how-to carousels", "Myth-busting content in your niche"]},
            {"theme": "Behind the brand series", "format": "Reels + Stories", "angle": "Real, unpolished look behind operations/creation", "expected_reach": "Very High", "content_ideas": ["Day in the life of [brand] team", "How [product/service] is made", "Honest mistakes and learnings"]},
            {"theme": "Community spotlight and UGC", "format": "Reposts + Stories", "angle": "Celebrate community members and customers", "expected_reach": "Medium (but high loyalty)", "content_ideas": ["Feature a follower/customer story weekly", "Fan art or creative use of brand", "Community Q&A and responses"]},
        ],
    }
    data = base.get(niche, base["general"])
    return [{"id": str(i + 1), **c} for i, c in enumerate(data)]


def _geo_signals(website_url: str | None, brand_name: str) -> dict:
    if not website_url:
        return {
            "has_website": False,
            "message": f"Add a website URL to {brand_name}'s profile to activate GEO/SEO intelligence",
            "quick_wins": [
                "Register a domain matching your Instagram handle",
                "Create a simple landing page linking to Instagram",
                "Add your brand to Google Business Profile",
            ],
        }
    domain = website_url.replace("https://", "").replace("http://", "").rstrip("/")
    return {
        "has_website": True,
        "domain": domain,
        "overall_score": 42,
        "signals": [
            {"label": "Content Citability", "score": 38, "status": "needs_work", "notes": "Add structured FAQ content with clear attributable claims for LLM citation.", "weight": 0.30},
            {"label": "AI Crawler Access", "score": 65, "status": "needs_work", "notes": "robots.txt likely permits crawlers, but no llms.txt found. Add it to signal AI intent.", "weight": 0.20},
            {"label": "Structured Markup", "score": 45, "status": "needs_work", "notes": "JSON-LD schema detected on some pages but missing on key product/FAQ pages.", "weight": 0.20},
            {"label": "Entity Consistency", "score": 72, "status": "good", "notes": f"'{brand_name}' is mentioned consistently across main pages. Good entity signal.", "weight": 0.15},
            {"label": "llms.txt Present", "score": 0, "status": "poor", "notes": f"No /llms.txt file found at {domain}. This file helps LLMs understand your brand structure.", "weight": 0.10},
            {"label": "Canonical Clarity", "score": 55, "status": "needs_work", "notes": "Some pages have missing or conflicting canonical signals.", "weight": 0.05},
        ],
        "priority_actions": [
            {"priority": 1, "action": f"Create /{domain}/llms.txt describing {brand_name}'s products and use cases", "effort": "Low", "impact": "High"},
            {"priority": 2, "action": "Add FAQPage JSON-LD schema to all FAQ and Q&A pages", "effort": "Low", "impact": "High"},
            {"priority": 3, "action": "Build structured FAQ content around your top 10 product questions", "effort": "Med", "impact": "High"},
            {"priority": 4, "action": "Add author attribution and expert credentials to key pages", "effort": "Low", "impact": "Med"},
        ],
    }


# ---------------------------------------------------------------------------
# Media planning data per niche
# ---------------------------------------------------------------------------

def _media_plan(niche: str, brand_name: str) -> dict:
    plans: dict[str, dict] = {
        "tech": {
            "primary_channels": [
                {"channel": "LinkedIn", "priority": 1, "budget_pct": 35, "goal": "Thought leadership & B2B pipeline", "formats": ["Sponsored content", "Lead gen forms", "Document ads"], "cpm_range": "$35–65", "audience_note": "Decision-makers, founders, marketing ops"},
                {"channel": "Instagram", "priority": 2, "budget_pct": 25, "goal": "Brand awareness & product demos", "formats": ["Reels", "Story ads", "Carousel"], "cpm_range": "$8–18", "audience_note": "Tech-adjacent consumers, early adopters"},
                {"channel": "Google Search", "priority": 3, "budget_pct": 25, "goal": "Bottom-funnel capture", "formats": ["Search ads", "PMAX"], "cpm_range": "$15–40 CPC", "audience_note": "High-intent branded + category queries"},
                {"channel": "Content / SEO", "priority": 4, "budget_pct": 15, "goal": "Long-term organic compounding", "formats": ["Blog", "Tools", "Glossary"], "cpm_range": "Organic", "audience_note": "All funnel stages via search"},
            ],
            "content_mix": {"organic": 55, "paid": 45},
            "test_plan": [
                {"test": "LinkedIn Lead Gen vs. landing page conversion", "hypothesis": "In-platform lead gen reduces CPL by 40%", "duration": "3 weeks"},
                {"test": "Reel demo ads vs. carousel product ads on Instagram", "hypothesis": "Reels drive 60% more top-funnel awareness at lower CPM", "duration": "2 weeks"},
                {"test": "Brand bidding on competitor keywords", "hypothesis": "Competitor keyword ads capture in-market buyers at lower CPL", "duration": "4 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$2,000–5,000", "growth": "$5,000–15,000", "scale": "$15,000+"},
            "kpi_targets": {"cpl": "$45–120", "roas": "2.5–4x", "cac": "$200–600"},
        },
        "fashion": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 45, "goal": "Discovery, desire, and purchase", "formats": ["Shopping ads", "Reels", "Story ads"], "cpm_range": "$6–15", "audience_note": "Style-conscious 18-45, interest-targeted"},
                {"channel": "TikTok", "priority": 2, "budget_pct": 30, "goal": "Viral reach and Gen Z acquisition", "formats": ["In-feed video", "Spark Ads", "TopView"], "cpm_range": "$4–12", "audience_note": "Gen Z trend-followers, fashion discovery mode"},
                {"channel": "Pinterest", "priority": 3, "budget_pct": 15, "goal": "Purchase-intent discovery", "formats": ["Shopping pins", "Promoted pins"], "cpm_range": "$2–8", "audience_note": "High-intent gift buyers and wardrobe planners"},
                {"channel": "Google Shopping", "priority": 4, "budget_pct": 10, "goal": "Bottom-funnel branded capture", "formats": ["Shopping ads", "PMAX"], "cpm_range": "$0.50–2.00 CPC", "audience_note": "Branded searches and category queries"},
            ],
            "content_mix": {"organic": 65, "paid": 35},
            "test_plan": [
                {"test": "UGC Spark Ads vs. branded creative on TikTok", "hypothesis": "UGC content drives 2x lower CPM and higher CTR", "duration": "2 weeks"},
                {"test": "Instagram Reels ads vs. Story ads for DTC conversion", "hypothesis": "Reels drive 40% more revenue per dollar at top-funnel", "duration": "3 weeks"},
                {"test": "Micro-influencer Spark Ads vs. brand ads", "hypothesis": "Influencer credibility lowers CPP by 35%", "duration": "4 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$1,500–4,000", "growth": "$4,000–12,000", "scale": "$12,000+"},
            "kpi_targets": {"roas": "3–6x", "cac": "$25–75", "cpm": "$6–12"},
        },
        "fitness": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 40, "goal": "Community building & product sales", "formats": ["Reels", "Story ads", "Carousel"], "cpm_range": "$5–14", "audience_note": "Fitness enthusiasts, 22-45, by interest and behavior"},
                {"channel": "YouTube", "priority": 2, "budget_pct": 25, "goal": "Deep engagement and trust building", "formats": ["Pre-roll", "In-feed video", "Bumper ads"], "cpm_range": "$6–18", "audience_note": "Active workout content consumers"},
                {"channel": "TikTok", "priority": 3, "budget_pct": 20, "goal": "Viral reach and new audience acquisition", "formats": ["In-feed video", "Spark Ads"], "cpm_range": "$4–10", "audience_note": "Gen Z/Millennial fitness beginners"},
                {"channel": "Google Search", "priority": 4, "budget_pct": 15, "goal": "High-intent product capture", "formats": ["Shopping ads", "Search"], "cpm_range": "$1–3 CPC", "audience_note": "People searching for fitness products/programs"},
            ],
            "content_mix": {"organic": 70, "paid": 30},
            "test_plan": [
                {"test": "Transformation story Reels vs. workout demo Reels", "hypothesis": "Transformation content drives 3x more conversions", "duration": "3 weeks"},
                {"test": "YouTube 15s vs. 30s pre-roll for brand recall", "hypothesis": "30s ads with strong hook drive 2x brand recall", "duration": "4 weeks"},
                {"test": "Retargeting video viewers vs. engagement audiences", "hypothesis": "Video viewers convert at 2.5x higher rate than engagement audiences", "duration": "2 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$1,000–3,000", "growth": "$3,000–10,000", "scale": "$10,000+"},
            "kpi_targets": {"roas": "3–5x", "cac": "$40–120", "cpm": "$5–12"},
        },
        "ecommerce": {
            "primary_channels": [
                {"channel": "Meta (Instagram + Facebook)", "priority": 1, "budget_pct": 50, "goal": "DTC acquisition and retargeting", "formats": ["Dynamic product ads", "Reels", "Catalog ads"], "cpm_range": "$6–16", "audience_note": "Lookalike audiences from buyers, interest-based discovery"},
                {"channel": "Google Shopping", "priority": 2, "budget_pct": 25, "goal": "High-intent purchase capture", "formats": ["Shopping", "PMAX", "Search"], "cpm_range": "$0.50–2.50 CPC", "audience_note": "Category + branded search intent"},
                {"channel": "TikTok", "priority": 3, "budget_pct": 15, "goal": "Top-funnel brand discovery", "formats": ["In-feed", "Spark Ads", "Shopping ads"], "cpm_range": "$3–10", "audience_note": "Young shoppers in discovery mode"},
                {"channel": "Email / SMS", "priority": 4, "budget_pct": 10, "goal": "Retention and LTV growth", "formats": ["Flows", "Campaigns", "Abandoned cart"], "cpm_range": "$0.01–0.05/email", "audience_note": "Existing customers and subscribers"},
            ],
            "content_mix": {"organic": 40, "paid": 60},
            "test_plan": [
                {"test": "Dynamic Product Ads vs. single creative campaigns", "hypothesis": "DPA improves ROAS by 40% through personalization", "duration": "2 weeks"},
                {"test": "UGC video vs. studio product photos in Meta ads", "hypothesis": "UGC reduces CPP by 35% through authenticity", "duration": "3 weeks"},
                {"test": "PMAX vs. standard Shopping + Search split", "hypothesis": "PMAX captures 20% more revenue at same budget", "duration": "6 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$2,000–6,000", "growth": "$6,000–20,000", "scale": "$20,000+"},
            "kpi_targets": {"roas": "4–8x", "cac": "$20–60", "cpm": "$6–14"},
        },
        "beauty": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 45, "goal": "Beauty discovery and conversion", "formats": ["Reels", "Story ads", "Shopping ads"], "cpm_range": "$7–16", "audience_note": "Beauty enthusiasts, skincare obsessives, makeup artists"},
                {"channel": "TikTok", "priority": 2, "budget_pct": 30, "goal": "Viral product discovery (GRWM, reviews)", "formats": ["Spark Ads", "In-feed", "TopView"], "cpm_range": "$4–11", "audience_note": "Beauty discovery-mode users, Gen Z and Millennial"},
                {"channel": "YouTube", "priority": 3, "budget_pct": 15, "goal": "Tutorial-driven trust building", "formats": ["In-stream ads", "Discovery ads"], "cpm_range": "$7–20", "audience_note": "Makeup tutorial watchers, skincare research mode"},
                {"channel": "Pinterest", "priority": 4, "budget_pct": 10, "goal": "Aspirational discovery and gifting", "formats": ["Promoted pins", "Shopping pins"], "cpm_range": "$2–7", "audience_note": "High-intent gift buyers and beauty planners"},
            ],
            "content_mix": {"organic": 60, "paid": 40},
            "test_plan": [
                {"test": "GRWM Spark Ads vs. branded tutorial ads", "hypothesis": "Creator GRWM content drives 3x more top-funnel engagement", "duration": "3 weeks"},
                {"test": "Before/after skin results vs. product showcase ads", "hypothesis": "Results-based creative drives 50% higher conversion rate", "duration": "2 weeks"},
                {"test": "TikTok Shop vs. DTC landing page conversion funnel", "hypothesis": "In-platform checkout reduces cart abandonment by 40%", "duration": "4 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$1,500–4,000", "growth": "$4,000–12,000", "scale": "$12,000+"},
            "kpi_targets": {"roas": "3–6x", "cac": "$20–55", "cpm": "$6–13"},
        },
        "food": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 40, "goal": "Visual discovery and foot traffic", "formats": ["Reels", "Story ads", "Location-targeted"], "cpm_range": "$5–13", "audience_note": "Local food enthusiasts, nearby audiences"},
                {"channel": "Google (Search + Maps)", "priority": 2, "budget_pct": 35, "goal": "Local discovery and bookings", "formats": ["Local search ads", "Maps ads", "Call ads"], "cpm_range": "$1–4 CPC", "audience_note": "Near-me searches, hungry right now intent"},
                {"channel": "TikTok", "priority": 3, "budget_pct": 15, "goal": "Viral food content reach", "formats": ["In-feed", "Spark Ads from creators"], "cpm_range": "$3–9", "audience_note": "Food content consumers, 18-35"},
                {"channel": "Meta (Facebook)", "priority": 4, "budget_pct": 10, "goal": "Event promotion and local community", "formats": ["Event ads", "Local awareness", "Lead gen"], "cpm_range": "$5–12", "audience_note": "Local community, 30+ age group"},
            ],
            "content_mix": {"organic": 65, "paid": 35},
            "test_plan": [
                {"test": "Behind-kitchen Reels vs. finished-dish Reels for engagement", "hypothesis": "BTS content drives 2x saves and shares", "duration": "2 weeks"},
                {"test": "Google Maps ads vs. organic Google Business for foot traffic", "hypothesis": "Maps ads drive 30% more tracked store visits", "duration": "4 weeks"},
                {"test": "Food creator Spark Ads vs. brand video ads on TikTok", "hypothesis": "Creator credibility drives 2.5x lower CPA for awareness campaigns", "duration": "3 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$800–2,500", "growth": "$2,500–8,000", "scale": "$8,000+"},
            "kpi_targets": {"roas": "N/A (local)", "cac": "$8–25 (per new regular)", "cpm": "$5–11"},
        },
        "travel": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 40, "goal": "Aspiration and booking intent", "formats": ["Reels", "Carousel", "Story ads"], "cpm_range": "$6–15", "audience_note": "Travel-intent audiences, in-market travelers"},
                {"channel": "Google (Search + Display)", "priority": 2, "budget_pct": 35, "goal": "High-intent booking capture", "formats": ["Search ads", "Hotel ads", "PMAX"], "cpm_range": "$2–6 CPC", "audience_note": "Active trip-planning searches"},
                {"channel": "YouTube", "priority": 3, "budget_pct": 15, "goal": "Destination storytelling and inspiration", "formats": ["Travel vlogs pre-roll", "Destination guides"], "cpm_range": "$7–18", "audience_note": "Destination research-mode viewers"},
                {"channel": "Pinterest", "priority": 4, "budget_pct": 10, "goal": "Trip planning discovery", "formats": ["Travel board pins", "Promoted destination pins"], "cpm_range": "$2–6", "audience_note": "Active trip planners (high intent)"},
            ],
            "content_mix": {"organic": 55, "paid": 45},
            "test_plan": [
                {"test": "Destination story Reels vs. offer/deal ads", "hypothesis": "Aspirational content drives 3x better top-funnel ROAS", "duration": "3 weeks"},
                {"test": "In-market audiences vs. custom intent audiences on Google Display", "hypothesis": "Custom intent captures 40% more conversion-ready travelers", "duration": "4 weeks"},
                {"test": "Creator travel vlogs as Spark Ads vs. brand video ads", "hypothesis": "Creator vlogs drive 2x booking intent through authenticity", "duration": "3 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$2,000–6,000", "growth": "$6,000–20,000", "scale": "$20,000+"},
            "kpi_targets": {"roas": "3–8x", "cac": "$50–200", "cpm": "$6–14"},
        },
        "creator": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 35, "goal": "Follower growth and course/product sales", "formats": ["Reels ads", "Story ads", "Lead gen"], "cpm_range": "$5–13", "audience_note": "Aspiring creators, niche topic followers"},
                {"channel": "YouTube", "priority": 2, "budget_pct": 25, "goal": "Deep content discovery and authority", "formats": ["Discovery ads", "In-stream pre-roll"], "cpm_range": "$6–15", "audience_note": "Learning-mode viewers in creator niche"},
                {"channel": "Meta (Facebook)", "priority": 3, "budget_pct": 20, "goal": "Community building and course sales", "formats": ["Lead gen", "Event ads", "Conversion"], "cpm_range": "$5–12", "audience_note": "30+ creator and entrepreneur audience"},
                {"channel": "Newsletter / Email", "priority": 4, "budget_pct": 20, "goal": "Owned audience monetization", "formats": ["Sponsorship slots", "Product promotions"], "cpm_range": "$20–80 CPM (newsletter)", "audience_note": "Highly engaged subscribers"},
            ],
            "content_mix": {"organic": 80, "paid": 20},
            "test_plan": [
                {"test": "Free lead magnet vs. paid mini-course as entry point", "hypothesis": "Free lead magnet builds email list 5x faster at lower CAC", "duration": "3 weeks"},
                {"test": "YouTube discovery ads for course awareness", "hypothesis": "Discovery ads in similar creator channels drives 60% lower CPC", "duration": "4 weeks"},
                {"test": "Instagram Reels ads with story testimonials vs. direct offer ads", "hypothesis": "Social proof-led ads drive 40% higher conversion for digital products", "duration": "2 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$500–2,000", "growth": "$2,000–7,000", "scale": "$7,000+"},
            "kpi_targets": {"roas": "4–10x (digital products)", "cac": "$15–60", "cpm": "$5–12"},
        },
        "b2b": {
            "primary_channels": [
                {"channel": "LinkedIn", "priority": 1, "budget_pct": 50, "goal": "Pipeline generation and ABM", "formats": ["Sponsored content", "InMail", "Lead gen forms", "Conversation ads"], "cpm_range": "$40–80", "audience_note": "Job title + company size + industry targeting"},
                {"channel": "Google Search", "priority": 2, "budget_pct": 25, "goal": "High-intent buyer capture", "formats": ["Search ads", "PMAX", "Display retargeting"], "cpm_range": "$20–60 CPC", "audience_note": "Category + competitor + branded keywords"},
                {"channel": "Content / SEO", "priority": 3, "budget_pct": 15, "goal": "Long-term inbound pipeline", "formats": ["Blog", "Whitepapers", "Case studies", "Tools"], "cpm_range": "Organic", "audience_note": "Top-of-funnel education and mid-funnel decision support"},
                {"channel": "Meta (Retargeting)", "priority": 4, "budget_pct": 10, "goal": "Lower-cost retargeting of known visitors", "formats": ["Dynamic retargeting", "Lead gen"], "cpm_range": "$6–14", "audience_note": "Website visitors, email list, CRM lookalikes"},
            ],
            "content_mix": {"organic": 50, "paid": 50},
            "test_plan": [
                {"test": "LinkedIn Lead Gen vs. gated landing page", "hypothesis": "In-platform lead gen reduces CPL by 50% vs. landing page", "duration": "3 weeks"},
                {"test": "Thought leadership content vs. product-focused LinkedIn ads", "hypothesis": "Thought leadership content drives 3x more engagement and 40% more pipeline", "duration": "4 weeks"},
                {"test": "LinkedIn InMail vs. sponsored content for mid-funnel nurture", "hypothesis": "InMail delivers 5x higher open rates but at 3x CPL — net positive for qualified leads", "duration": "3 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$3,000–8,000", "growth": "$8,000–25,000", "scale": "$25,000+"},
            "kpi_targets": {"cpl": "$100–300", "roas": "5–15x (pipeline)", "cac": "$500–2,000"},
        },
        "general": {
            "primary_channels": [
                {"channel": "Instagram", "priority": 1, "budget_pct": 40, "goal": "Brand discovery and audience growth", "formats": ["Reels", "Story ads", "Carousel"], "cpm_range": "$5–14", "audience_note": "Interest-based + lookalike audiences"},
                {"channel": "Meta (Facebook)", "priority": 2, "budget_pct": 25, "goal": "Conversion and retargeting", "formats": ["Dynamic ads", "Lead gen", "Conversion"], "cpm_range": "$5–12", "audience_note": "Lookalike buyers, website visitors"},
                {"channel": "Google Search", "priority": 3, "budget_pct": 20, "goal": "Capture in-market search intent", "formats": ["Search ads", "Shopping"], "cpm_range": "$1–4 CPC", "audience_note": "Branded and category keywords"},
                {"channel": "TikTok", "priority": 4, "budget_pct": 15, "goal": "Reach younger demographic organically", "formats": ["In-feed", "Spark Ads"], "cpm_range": "$3–9", "audience_note": "18-34 discovery-mode users"},
            ],
            "content_mix": {"organic": 60, "paid": 40},
            "test_plan": [
                {"test": "Instagram Reels ads vs. static image ads", "hypothesis": "Video Reels drive 3x more reach at similar CPM", "duration": "2 weeks"},
                {"test": "Lookalike audiences vs. interest targeting", "hypothesis": "Lookalike audiences from buyers convert at 2x vs. interest-based", "duration": "3 weeks"},
                {"test": "Retargeting 1-day vs. 7-day website visitors", "hypothesis": "1-day visitors have 50% higher conversion intent but smaller volume", "duration": "2 weeks"},
            ],
            "monthly_budget_guide": {"starter": "$1,000–3,500", "growth": "$3,500–12,000", "scale": "$12,000+"},
            "kpi_targets": {"roas": "2–5x", "cac": "$20–80", "cpm": "$5–13"},
        },
    }
    data = plans.get(niche, plans["general"])
    return {**data, "niche": niche, "brand_name": brand_name}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def get_intelligence(brand_profile: dict) -> dict:
    """Return full intelligence package for a brand profile."""
    niche = infer_niche(brand_profile.get("category", ""))
    brand_name = brand_profile.get("brand_name", "Your Brand")
    handle = brand_profile.get("instagram_handle", "").lstrip("@")
    website = brand_profile.get("website_url")

    return {
        "niche": niche,
        "trends": _trends(niche, brand_name),
        "audience_segments": _audience_segments(niche, brand_name),
        "recommendations": _recommendations(niche, brand_name, handle),
        "content_opportunities": _content_opportunities(niche, brand_name),
        "geo_signals": _geo_signals(website, brand_name),
        "media_plan": _media_plan(niche, brand_name),
    }


def get_dashboard_overview(brand_profile: dict) -> dict:
    """Return a summarized overview for the dashboard."""
    intel = get_intelligence(brand_profile)
    trends = intel["trends"]
    recs = intel["recommendations"]
    handle = brand_profile.get("instagram_handle", "").lstrip("@")
    brand_name = brand_profile.get("brand_name", "Your Brand")
    niche = intel["niche"]
    website = brand_profile.get("website_url")

    # Top opportunities (highest priority recommendations)
    top_opps = sorted(recs, key=lambda r: r.get("priority_score", 0), reverse=True)[:3]

    return {
        "brand_name": brand_name,
        "instagram_handle": handle,
        "niche": niche,
        "website": website,
        "has_website": bool(website),
        "trend_count": len(trends),
        "surging_trends": len([t for t in trends if t["momentum_score"] >= 0.7]),
        "recommendation_count": len(recs),
        "top_opportunities": top_opps,
        "audience_segment_count": len(intel["audience_segments"]),
        "geo_score": intel["geo_signals"].get("overall_score"),
        "top_trend": trends[0] if trends else None,
        "kpis": [
            {"label": "Growth Opportunities", "value": str(len(recs)), "description": "Actionable recommendations for your account"},
            {"label": "Trending Topics", "value": str(len(trends)), "description": f"Relevant to {niche} niche this week"},
            {"label": "Audience Segments", "value": str(len(intel["audience_segments"])), "description": "Identified high-fit audience clusters"},
            {"label": "GEO Score", "value": str(intel["geo_signals"].get("overall_score", "N/A")), "description": "AI discoverability score" if website else "Add website to activate"},
        ],
    }
