# 🕵️ Intel Shop Design - COMPLETE

## ✅ Serious Intelligence Agency Aesthetic

Successfully implemented a professional intelligence shop interface with subtle "something's off" vibes.

### 🎨 **Design System**

**Color Palette:**
- `ink` (#0E0E12) - Deep background
- `bone` (#F5F5F0) - Primary text 
- `ash` (#1A1A22) - Card backgrounds
- `fog` (#B9B9B3) - Secondary text
- `gild` (#C2A75E) - Gold accents
- `alert` (#FA5A5A) - Risk indicators
- `limewire` (#59D3A2) - Link accents

**Typography:**
- Headers: Source Serif 4 (institutional authority)
- Body: Inter (clean readability)
- Code: JetBrains Mono

**Liminal Effects:**
- Subtle grain overlay (mix-blend-mode)
- Radial grid pattern
- RGB shadow split on hover
- Slow scale transforms
- Backdrop blur navigation

### 🌐 **ENG/FI Language Split**

**Clean URL Structure:**
- `/en/newswire` - English feed
- `/fi/newswire` - Finnish feed
- `/en/category/geopolitics` - Category filtering
- `/en/article/article-id` - Article detail

**Language Detection:**
- Path-based detection
- Persistent toggle
- All links respect current language

### 📰 **News Card Design**

**Visual Hierarchy:**
1. **Kicker** (gold, small caps, tracking)
2. **Headline** (serif, large)
3. **Lede** (readable summary)
4. **Why it matters** (context)
5. **Risk scenario** (red alert styling)
6. **Sources** (linked, credible)

**Image Treatment:**
- Duotone filter (grayscale + contrast)
- Slow zoom on hover
- Vignette overlays
- Fallback to category-specific Unsplash

### 🏛️ **Categories**

- Geopolitics
- Information Operations  
- Espionage & Intelligence
- High Politics
- Secret History
- Elite Analysis
- Special Reports

### 📱 **Responsive Features**

- Card grid (2-col desktop, 1-col mobile)
- Sticky navigation with backdrop blur
- Smooth animations (cubic-bezier easing)
- Touch-friendly interactions

### 🔒 **Dark Tolerance Validation**

Backend validation ensures:
- ✅ Risk scenarios present
- ✅ "Why it matters" filled
- ✅ 2+ credible sources
- ✅ No vague hedging language
- ❌ Build fails if content too generic

### 🚀 **Build Process**

```bash
# Development
make fe-symlink-feeds  # Copy feeds to public
cd web && npm run dev  # Start dev server

# Production  
make fe-build         # Build with feeds
make fe-deploy        # Deploy to GCS
```

### 🌟 **Key Features**

1. **Professional Authority** - Serif headers, clean margins, institutional feel
2. **Subtle Unease** - Grain texture, slow animations, RGB glitches
3. **Intelligence Focus** - Risk scenarios, source credibility, threat analysis
4. **Bilingual Support** - Clean ENG/FI separation with shared components
5. **Mobile Optimized** - Responsive cards, touch navigation
6. **Performance** - Lazy loading, optimized images, short cache times

### 🎯 **Live URLs**

- **English**: `/en/newswire`
- **Finnish**: `/fi/newswire`
- **Category**: `/en/category/geopolitics`
- **Article**: `/en/article/article-id`

### 💼 **"Expensive" Look Achieved With:**

- High-contrast typography combinations
- Generous whitespace and breathing room
- Subtle gold accents (not flashy)
- Professional photography treatment
- Smooth, considered animations
- Institutional navigation structure
- Source attribution and credibility signals

The design successfully balances **serious intelligence authority** with **subtle psychological unease** - exactly what a paranoid intelligence service would look like. 🕵️‍♂️
