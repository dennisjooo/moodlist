"""Centralized regional, language, and theme filtering utilities."""

from typing import List, Optional


class RegionalFilter:
    """Handles regional, language, and theme-based filtering for artists and tracks."""

    # Language indicators for track name detection
    LANGUAGE_INDICATORS = {
        "spanish": ["el ", "la ", "los ", "las ", "mi ", "tu ", "de ", "con ", "por ", "para "],
        "korean": ["\u3131", "\u314f", "\uac00", "\ud7a3"],  # Hangul character ranges
        "japanese": ["\u3040", "\u309f", "\u30a0", "\u30ff"],  # Hiragana/Katakana
        "chinese": ["\u4e00", "\u9fff"],  # Common CJK
        "portuguese": ["meu ", "minha ", "você ", "está ", "muito ", "bem "],
        "indonesian": ["aku ", "kamu ", "yang ", "dengan ", "untuk ", "dari ", "ini ", "itu ", "dan ", "atau "],
        "malay": ["saya ", "kita ", "kami ", "awak ", "dengan ", "untuk ", "dari "],
        "german": ["der ", "die ", "das ", "ich ", "du ", "und ", "mit "],
        "french": ["le ", "la ", "les ", "de ", "je ", "tu ", "avec ", "pour "]
    }

    # Language to region mapping
    LANGUAGE_TO_REGION = {
        "spanish": "Latin American",
        "portuguese": "Latin American",
        "korean": "East Asian",
        "japanese": "East Asian",
        "chinese": "East Asian",
        "indonesian": "Southeast Asian",
        "malay": "Southeast Asian",
        "german": "European",
        "french": "European"
    }

    # Genre-based region indicators for artist detection
    GENRE_REGION_INDICATORS = {
        "Southeast Asian": ['indonesian', 'malay', 'malaysian', 'singapore', 'thai', 'vietnamese', 'filipino'],
        "East Asian": ['k-pop', 'korean', 'j-pop', 'japanese', 'c-pop', 'chinese', 'mandopop', 'cantopop'],
        "Latin American": ['latin', 'reggaeton', 'bachata', 'salsa', 'cumbia', 'banda', 'corridos', 'urbano latino'],
        "Eastern European": ['russian', 'polish', 'ukrainian', 'balkan', 'romanian'],
        "Middle Eastern": ['arabic', 'turkish', 'persian', 'khaleeji'],
        "African": ['afrobeats', 'afropop', 'nigerian', 'south african', 'amapiano']
    }

    # Flexible region matching (e.g., "Western" includes multiple sub-regions)
    REGION_ALIASES = {
        "western": ["american", "european", "british", "canadian", "australian"],
        "european": ["french", "german", "italian", "spanish", "portuguese", "british"]
    }

    @classmethod
    def detect_track_region(cls, track_name: str, artists: List[str]) -> Optional[str]:
        """Detect the likely region/origin of a track based on language indicators in track/artist names.

        Args:
            track_name: Track name
            artists: List of artist names

        Returns:
            Detected region or None
        """
        track_and_artists = (track_name + " " + " ".join(artists)).lower()

        # Check for each language's indicators
        for language, indicators in cls.LANGUAGE_INDICATORS.items():
            for indicator in indicators:
                if isinstance(indicator, str):
                    if indicator in track_and_artists:
                        return cls.LANGUAGE_TO_REGION.get(language, language.capitalize())
                else:
                    # Unicode range check for CJK languages
                    for char in track_and_artists:
                        if indicator <= char <= indicators[indicators.index(indicator) + 1]:
                            return cls.LANGUAGE_TO_REGION.get(language, language.capitalize())

        return None

    @classmethod
    def detect_artist_region(cls, artist_name: str, genres: List[str]) -> Optional[str]:
        """Detect the likely region/origin of an artist based on genres.

        Args:
            artist_name: Name of the artist
            genres: List of Spotify genres for the artist

        Returns:
            Detected region or None
        """
        genres_lower = ' '.join(genres).lower()

        # Check each region's genre indicators
        for region, genre_indicators in cls.GENRE_REGION_INDICATORS.items():
            if any(g in genres_lower for g in genre_indicators):
                return region

        return None

    @classmethod
    def is_region_excluded(cls, detected_region: str, excluded_regions: List[str]) -> bool:
        """Check if detected region matches any excluded region.

        Args:
            detected_region: Detected artist/track region
            excluded_regions: List of regions to exclude

        Returns:
            True if region should be excluded
        """
        if not detected_region or not excluded_regions:
            return False

        detected_lower = detected_region.lower()
        excluded_lower = [r.lower() for r in excluded_regions]

        # Direct match
        if detected_lower in excluded_lower:
            return True

        # Partial match (e.g., "Southeast Asian" contains "asian")
        for excluded in excluded_lower:
            if excluded in detected_lower or detected_lower in excluded:
                return True

        return False

    @classmethod
    def region_matches_preferred(cls, detected_region: str, preferred_regions: List[str]) -> bool:
        """Check if detected region matches any preferred region with flexible matching.

        Args:
            detected_region: Detected artist/track region
            preferred_regions: List of preferred regions

        Returns:
            True if region matches
        """
        if not detected_region or not preferred_regions:
            return False

        detected_lower = detected_region.lower()
        preferred_lower = [r.lower() for r in preferred_regions]

        # Direct match
        if detected_lower in preferred_lower:
            return True

        # Check region aliases (e.g., "Western" includes "American", "European", etc.)
        for pref in preferred_lower:
            if pref in cls.REGION_ALIASES:
                aliases = cls.REGION_ALIASES[pref]
                if any(alias in detected_lower for alias in aliases):
                    return True

        # Partial match (e.g., "Latin American" matches "latin")
        if any(pref in detected_lower or detected_lower in pref for pref in preferred_lower):
            return True

        return False

    @classmethod
    def validate_regional_compatibility(
        cls,
        detected_region: Optional[str],
        preferred_regions: List[str],
        excluded_regions: List[str]
    ) -> tuple[bool, str]:
        """Validate if a detected region is compatible with mood preferences.

        Args:
            detected_region: Detected region (or None if couldn't detect)
            preferred_regions: List of preferred regions from mood analysis
            excluded_regions: List of excluded regions from mood analysis

        Returns:
            (is_valid, reason) - True if region is compatible, False with reason if not
        """
        # If no regional constraints, skip
        if not preferred_regions and not excluded_regions:
            return (True, "No regional constraints")

        # If we can't detect region, allow it (be lenient)
        if not detected_region:
            return (True, "Region could not be determined")

        # Check if region is explicitly excluded
        if excluded_regions and cls.is_region_excluded(detected_region, excluded_regions):
            return (False, f"Regional mismatch: detected region '{detected_region}' is in excluded regions {excluded_regions}")

        # Check if region matches preferred (if specified)
        if preferred_regions and not cls.region_matches_preferred(detected_region, preferred_regions):
            return (False, f"Regional mismatch: detected region '{detected_region}', expected one of {preferred_regions}")

        return (True, "Region matches mood intent")

    # Theme filtering - Keyword patterns for different themes
    THEME_INDICATORS = {
        "holiday": ["christmas", "xmas", "santa", "jingle", "sleigh", "noel", "holiday",
                   "winter wonderland", "silent night", "holy night", "feliz navidad",
                   "deck the halls", "carol", "festive"],
        "christmas": ["christmas", "xmas", "santa", "jingle", "sleigh", "noel",
                     "silent night", "holy night", "feliz navidad", "deck the halls"],
        "religious": ["holy", "prayer", "worship", "gospel", "praise", "blessed", "amen",
                     "hallelujah", "church", "hymn", "psalm", "sacred"],
        "kids": ["baby shark", "wheels on the bus", "itsy bitsy", "twinkle twinkle",
                "abc song", "nursery rhyme", "children's", "kids bop"],
        "children": ["baby shark", "wheels on the bus", "itsy bitsy", "twinkle twinkle",
                    "abc song", "nursery rhyme", "children's", "kids bop"],
        "comedy": ["parody", "comedy", "funny", "joke", "weird al", "lonely island"],
        "parody": ["parody", "weird al", "lonely island", "comedy"],
        "national anthems": ["national anthem", "star spangled banner", "god save"],
        "patriotic": ["national anthem", "patriotic", "star spangled banner"],
        "sports": ["stadium anthem", "we will rock you", "we are the champions"],
        "stadium": ["stadium anthem", "we will rock you", "we are the champions"],
        "video game": ["8-bit", "chiptune", "minecraft", "fortnite", "game soundtrack"],
        "soundtrack": ["movie soundtrack", "film score", "ost"],
        "aggressive": ["rage", "angry", "screamo", "death metal", "brutal"]
    }

    @classmethod
    def validate_theme_compatibility(
        cls,
        track_name: str,
        excluded_themes: List[str]
    ) -> tuple[bool, str]:
        """Validate that track doesn't contain excluded themes.

        Args:
            track_name: Track name to check
            excluded_themes: List of themes to exclude

        Returns:
            (is_valid, reason) - True if themes compatible, False with reason if not
        """
        if not excluded_themes:
            return (True, "No themes excluded")

        track_lower = track_name.lower()

        for excluded_theme in excluded_themes:
            theme_lower = excluded_theme.lower()
            indicators = cls.THEME_INDICATORS.get(theme_lower, [theme_lower])

            for indicator in indicators:
                if indicator in track_lower:
                    return (False, f"Theme exclusion: track contains '{indicator}' which matches excluded theme '{excluded_theme}'")

        return (True, "No excluded themes detected")
