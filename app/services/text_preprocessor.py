"""
Text preprocessing service for TTS audio generation.

Normalizes financial figures, percentages, abbreviations, ticker symbols,
and company names to natural speech text suitable for OpenAI TTS.
"""
import re
import structlog
from num2words import num2words


logger = structlog.get_logger(__name__)


# Pronunciation dictionary for insurance/financial abbreviations
PRONUNCIATION_DICT = {
    # Spell-out abbreviations
    r'\bLLC\b': 'L L C',
    r'\bCEO\b': 'C E O',
    r'\bCFO\b': 'C F O',
    r'\bCIO\b': 'C I O',
    r'\bCOO\b': 'C O O',
    r'\bIPO\b': 'I P O',
    r'\bESG\b': 'E S G',
    r'\bCFD\b': 'C F D',
    r'\bABS\b': 'A B S',
    r'\bILS\b': 'I L S',
    r'\bD&O\b': 'D and O',
    r'\bE&O\b': 'E and O',
    r'\bFCA\b': 'F C A',
    r'\bNAIC\b': 'N A I C',
    r'\bAPRA\b': 'A P R A',
    r'\bPRA\b': 'P R A',
    r'\bIFRS\b': 'I F R S',
    r'\bGAAP\b': 'G A A P',

    # Expand abbreviations
    r'\bM&A\b': 'M and A',
    r'\bQ1\b': 'Q one',
    r'\bQ2\b': 'Q two',
    r'\bQ3\b': 'Q three',
    r'\bQ4\b': 'Q four',
    r'\bH1\b': 'H one',
    r'\bH2\b': 'H two',
    r'\bYoY\b': 'year over year',
    r'\bQoQ\b': 'quarter over quarter',
    r'\bbps?\b': 'basis points',
}


# Company name pronunciation dictionary
COMPANY_PRONUNCIATIONS = {
    r'\bAon\b': 'A-on',
    r'\bZurich\b': 'Zuurik',
    r'\bMunich Re\b': 'Myoonik Re',
    r'\bSCOR\b': 'S C O R',
    r'\bTokio Marine\b': 'Tokyo Marine',
    r'\bChubb\b': 'Chub',
    r'\bAIG\b': 'A I G',
    r'\bAllianz\b': 'Alli-ants',
    r'\bAXA\b': 'A X A',
    r'\bGeneral Re\b': 'General Re',
    r'\bHannover Re\b': 'Hannover Re',
    r'\bSwiss Re\b': 'Swiss Re',
    r'\bQBE\b': 'Q B E',
    r'\bBeazley\b': 'Beezley',
    r'\bHiscox\b': 'Hiscocks',
}


class TextPreprocessor:
    """
    Preprocesses text scripts for TTS audio generation.

    Converts financial terminology, percentages, abbreviations,
    ticker symbols, and company names to natural speech text.
    """

    def preprocess(self, script: str) -> str:
        """
        Apply all text preprocessing transformations for TTS.

        Args:
            script: Raw script text

        Returns:
            Preprocessed text suitable for TTS
        """
        logger.info("preprocessing_script", original_length=len(script))

        # Track transformations
        transformations = {
            'currency': 0,
            'percentages': 0,
            'abbreviations': 0,
            'tickers': 0,
            'companies': 0
        }

        # Apply transformations in order
        text, currency_count = self._normalize_currency(script)
        transformations['currency'] = currency_count

        text, percent_count = self._normalize_percentages(text)
        transformations['percentages'] = percent_count

        text, abbrev_count = self._normalize_abbreviations(text)
        transformations['abbreviations'] = abbrev_count

        text, ticker_count = self._normalize_tickers(text)
        transformations['tickers'] = ticker_count

        text, company_count = self._normalize_company_names(text)
        transformations['companies'] = company_count

        logger.info(
            "preprocessing_complete",
            transformations=transformations,
            preprocessed_length=len(text)
        )

        return text

    def _normalize_currency(self, text: str) -> tuple[str, int]:
        """
        Convert currency amounts to natural language.

        Examples:
            $1.2B -> "one point two billion dollars"
            $150M -> "one hundred fifty million dollars"
            $25K -> "twenty-five thousand dollars"
            $500 -> "five hundred dollars"
        """
        count = 0

        # Pattern order matters: match B/M/K suffixed amounts BEFORE plain dollar amounts

        # $X.XB / $X.X billion -> "X point X billion dollars"
        def replace_billion(match):
            nonlocal count
            count += 1
            num = float(match.group(1))
            if '.' in match.group(1):
                return f"{num2words(num, to='cardinal')} billion dollars"
            return f"{num2words(int(num), to='cardinal')} billion dollars"

        text = re.sub(r'\$(\d+\.?\d*)\s?(?:[Bb](?:illion)?|B)', replace_billion, text)

        # $X.XM / $X.X million -> "X point X million dollars"
        def replace_million(match):
            nonlocal count
            count += 1
            num = float(match.group(1))
            if '.' in match.group(1):
                return f"{num2words(num, to='cardinal')} million dollars"
            return f"{num2words(int(num), to='cardinal')} million dollars"

        text = re.sub(r'\$(\d+\.?\d*)\s?(?:[Mm](?:illion)?|M)', replace_million, text)

        # $X.XK / $X.X thousand -> "X point X thousand dollars"
        def replace_thousand(match):
            nonlocal count
            count += 1
            num = float(match.group(1))
            if '.' in match.group(1):
                return f"{num2words(num, to='cardinal')} thousand dollars"
            return f"{num2words(int(num), to='cardinal')} thousand dollars"

        text = re.sub(r'\$(\d+\.?\d*)\s?[Kk]', replace_thousand, text)

        # $X.X (plain dollar amounts) -> "X point X dollars"
        def replace_dollars(match):
            nonlocal count
            count += 1
            num = float(match.group(1))
            if '.' in match.group(1):
                return f"{num2words(num, to='cardinal')} dollars"
            return f"{num2words(int(num), to='cardinal')} dollars"

        text = re.sub(r'\$(\d+\.?\d*)', replace_dollars, text)

        return text, count

    def _normalize_percentages(self, text: str) -> tuple[str, int]:
        """
        Convert percentages to natural language.

        Examples:
            15.3% -> "fifteen point three percent"
            7% -> "seven percent"
        """
        count = 0

        def replace_percent(match):
            nonlocal count
            count += 1
            num_str = match.group(1)

            if '.' in num_str:
                integer_part, decimal_part = num_str.split('.')
                integer_words = num2words(int(integer_part), to='cardinal')
                decimal_words = num2words(int(decimal_part), to='cardinal')
                return f"{integer_words} point {decimal_words} percent"
            else:
                return f"{num2words(int(float(num_str)), to='cardinal')} percent"

        text = re.sub(r'(\d+\.?\d*)\s?%', replace_percent, text)

        return text, count

    def _normalize_abbreviations(self, text: str) -> tuple[str, int]:
        """
        Expand common insurance/financial abbreviations.

        Uses PRONUNCIATION_DICT for standardized replacements.
        """
        count = 0

        for pattern, replacement in PRONUNCIATION_DICT.items():
            matches = len(re.findall(pattern, text))
            if matches > 0:
                count += matches
                text = re.sub(pattern, replacement, text)

        return text, count

    def _normalize_tickers(self, text: str) -> tuple[str, int]:
        """
        Normalize ticker symbols to spoken form.

        Example:
            (AAPL) -> "A A P L"
        """
        count = 0

        def spell_ticker(match):
            nonlocal count
            count += 1
            ticker = match.group(1)
            # Spell out letters with spaces: AAPL -> "A A P L"
            return " ".join(ticker)

        # Pattern: (AAPL) - 2-5 uppercase letters in parentheses
        text = re.sub(r'\(([A-Z]{2,5})\)', spell_ticker, text)

        return text, count

    def _normalize_company_names(self, text: str) -> tuple[str, int]:
        """
        Apply pronunciation corrections for commonly mispronounced companies.

        Uses COMPANY_PRONUNCIATIONS dictionary.
        """
        count = 0

        for pattern, pronunciation in COMPANY_PRONUNCIATIONS.items():
            matches = len(re.findall(pattern, text))
            if matches > 0:
                count += matches
                text = re.sub(pattern, pronunciation, text)

        return text, count
