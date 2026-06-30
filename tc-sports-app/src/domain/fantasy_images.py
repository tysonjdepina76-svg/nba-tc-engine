"""Fantasy image generator — TC Sports App."""

from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from pathlib import Path
from typing import Optional, List
import hashlib
import logging
from datetime import datetime
from src.domain.entities import Player, Projection

logger = logging.getLogger(__name__)

class FantasyImageGenerator:
    def __init__(self, sport: str, cache_dir: str = "/tmp/tc_image_cache"):
        self.sport = sport
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._font_cache = {}
    
    def _get_font(self, size: int, style: str = "regular"):
        key = f"{style}_{size}"
        if key in self._font_cache:
            return self._font_cache[key]
        try:
            if style == "bold":
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
            else:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except Exception:
            font = ImageFont.load_default()
        self._font_cache[key] = font
        return font

    def _get_logo(self, team_name: str) -> Optional[Image.Image]:
        cache_key = hashlib.md5(team_name.encode()).hexdigest()
        cache_path = self.cache_dir / f"logo_{cache_key}.png"
        if cache_path.exists():
            return Image.open(cache_path)
        img = Image.new('RGBA', (100, 100), color=(26, 26, 46, 255))
        draw = ImageDraw.Draw(img)
        font = self._get_font(28, "bold")
        draw.text((50, 50), team_name[:3].upper(), fill='white', font=font, anchor='mm')
        img.save(cache_path)
        return img

    def generate_player_card(self, player: Player, projection: Projection, width: int = 400, height: int = 650) -> str:
        card = Image.new('RGB', (width, height), color='#0f0f1a')
        draw = ImageDraw.Draw(card)
        for i in range(height):
            r = 10 + int(15 * (i / height))
            g = 10 + int(8 * (i / height))
            b = 20 + int(22 * (i / height))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        draw.rectangle([(2, 2), (width-2, height-2)], outline='#2a2a4e', width=2)
        title_font = self._get_font(28, "bold")
        body_font = self._get_font(20, "regular")
        small_font = self._get_font(16, "regular")
        draw.text((20, 25), player.name, fill='white', font=title_font)
        draw.text((20, 70), f"{player.position} • {player.team}", fill='#a0a0b0', font=body_font)
        logo = self._get_logo(player.team).resize((70, 70))
        card.paste(logo, (width-95, 55), logo)
        box_y = 140
        draw.rectangle([(20, box_y), (width-20, box_y+180)], fill='#1a1a2e', outline='#2a2a4e', width=2)
        draw.text((40, box_y+20), "PROJECTED", fill='#666', font=small_font)
        draw.text((40, box_y+50), f"{projection.tc_projection:.1f}", fill='#4fc3f7', font=self._get_font(48, "bold"))
        draw.text((40, box_y+105), "POINTS", fill='#666', font=small_font)

        # Confidence proxy from edge (no confidence field in schema)
        conf_pct = min(95, max(40, 50 + projection.edge * 8))
        conf_color = '#4caf50' if conf_pct > 70 else '#ffa726' if conf_pct > 50 else '#e53935'
        draw.text((width-200, box_y+20), "EDGE STRENGTH", fill='#666', font=small_font)
        draw.text((width-200, box_y+50), f"{conf_pct:.0f}%", fill=conf_color, font=self._get_font(36, "bold"))
        edge_text = f"+{projection.edge:.1f}" if projection.edge > 0 else f"{projection.edge:.1f}"
        edge_color = '#4caf50' if projection.edge > 2 else '#ffa726' if projection.edge > 0 else '#e53935'
        draw.text((width-200, box_y+105), "EDGE", fill='#666', font=small_font)
        draw.text((width-200, box_y+135), edge_text, fill=edge_color, font=self._get_font(28, "bold"))
        draw.line([(20, height-40), (width-20, height-40)], fill='#2a2a4e', width=1)
        draw.text((20, height-30), f"TC Sports • {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill='#444', font=small_font)
        output_dir = Path("reports/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = player.name.replace(' ', '_').replace("'", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{self.sport}_{safe_name}_{timestamp}.png"
        card.save(filename)
        logger.info(f"Generated: {filename}")
        return str(filename)

    def generate_weekly_roundup(self, projections: List[Projection], top_n: int = 10) -> str:
        sorted_proj = sorted(projections, key=lambda p: p.tc_projection, reverse=True)[:top_n]
        height = 120 + (len(sorted_proj) * 50)
        width = 700
        card = Image.new('RGB', (width, height), color='#0f0f1a')
        draw = ImageDraw.Draw(card)
        title_font = self._get_font(32, "bold")
        body_font = self._get_font(20, "regular")
        draw.rectangle([(0, 0), (width, 80)], fill='#1a1a2e')
        draw.text((20, 20), f"TOP {top_n} PROJECTIONS", fill='#ffd54f', font=title_font)
        draw.text((20, 55), f"{self.sport} • {datetime.now().strftime('%B %d, %Y')}", fill='#666', font=body_font)
        y = 100
        for i, proj in enumerate(sorted_proj, 1):
            color = '#4fc3f7' if i <= 3 else '#a0a0b0'
            bg = '#1a1a2e' if i % 2 == 0 else '#151525'
            draw.rectangle([(10, y-5), (width-10, y+40)], fill=bg)
            medal = ['GOLD', 'SILV', 'BRONZE'][i-1] if i <= 3 else f"{i}."
            draw.text((20, y+5), f"{medal} {proj.player} ({proj.team}) — {proj.tc_projection:.1f} pts", fill=color, font=body_font)
            bar_pct = min(95, max(40, 50 + proj.edge * 8))
            bar_width = int(bar_pct * 1.0)
            draw.rectangle([(450, y+12), (450+bar_width, y+28)], fill='#4caf50' if bar_width > 70 else '#ffa726')
            draw.text((560, y+5), f"{bar_pct:.0f}%", fill='#666', font=body_font)
            y += 45
        output_dir = Path("reports/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{self.sport}_roundup_{timestamp}.png"
        card.save(filename)
        return str(filename)

    def generate_fight_card(self, fighter_a: str, fighter_b: str,
                            weight_class: str = "Main Event",
                            odds_a: int = -150, odds_b: int = +130,
                            prop: Optional[str] = None,
                            width: int = 800, height: int = 500) -> str:
        """BOXING/MMA fight card — head-to-head poster with odds + prop.

        Saves to reports/images/{SPORT}_FIGHTER_A_vs_FIGHTER_B_{ts}.png
        Returns the file path.
        """
        bg = '#0f0f1a' if self.sport == "BOXING" else '#10101a'
        ring_color = '#d50000' if self.sport == "BOXING" else '#1a237e'
        card = Image.new('RGB', (width, height), color=bg)
        draw = ImageDraw.Draw(card)
        # gradient
        for i in range(height):
            r = 10 + int(15 * (i / height))
            g = 10 + int(8 * (i / height))
            b = 20 + int(22 * (i / height))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        # frame
        draw.rectangle([(2, 2), (width-2, height-2)], outline=ring_color, width=4)
        # title bar
        title_font = self._get_font(36, "bold")
        sub_font = self._get_font(20, "regular")
        body_font = self._get_font(28, "bold")
        small_font = self._get_font(16, "regular")
        draw.rectangle([(0, 0), (width, 70)], fill='#1a1a2e')
        draw.text((20, 12), f"{self.sport} • {weight_class}", fill='#ffd54f', font=title_font)
        draw.text((20, 48), datetime.now().strftime('%B %d, %Y'), fill='#888', font=sub_font)

        # fighter A
        logo_a = self._get_logo(fighter_a).resize((110, 110))
        card.paste(logo_a, (40, 120), logo_a)
        draw.text((40, 245), fighter_a, fill='white', font=body_font)
        odds_a_str = f"{odds_a:+d}" if odds_a else "EVEN"
        draw.text((40, 285), f"Odds {odds_a_str}", fill='#4fc3f7', font=sub_font)

        # VS
        draw.text((width // 2 - 30, 175), "VS", fill=ring_color, font=self._get_font(64, "bold"))

        # fighter B
        logo_b = self._get_logo(fighter_b).resize((110, 110))
        card.paste(logo_b, (width - 150, 120), logo_b)
        draw.text((width - 290, 245), fighter_b, fill='white', font=body_font)
        odds_b_str = f"{odds_b:+d}" if odds_b else "EVEN"
        draw.text((width - 290, 285), f"Odds {odds_b_str}", fill='#4fc3f7', font=sub_font)

        # prop callout
        if prop:
            draw.rectangle([(20, height - 90), (width - 20, height - 30)], fill='#1a1a2e', outline=ring_color, width=2)
            draw.text((35, height - 80), "TC PROP", fill='#888', font=small_font)
            draw.text((35, height - 55), prop, fill='#4caf50', font=self._get_font(24, "bold"))

        # footer
        draw.line([(20, height - 18), (width - 20, height - 18)], fill=ring_color, width=1)
        draw.text((20, height - 14), f"TC Sports • {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill='#444', font=small_font)

        output_dir = Path("reports/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_a = fighter_a.replace(' ', '_').replace("'", '')
        safe_b = fighter_b.replace(' ', '_').replace("'", '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{self.sport}_{safe_a}_vs_{safe_b}_{timestamp}.png"
        card.save(filename)
        logger.info(f"Generated fight card: {filename}")
        return str(filename)
