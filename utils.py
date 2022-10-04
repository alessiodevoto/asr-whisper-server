import torchaudio
import torch
torchaudio.set_audio_backend("sox_io")
from torchaudio.functional import resample
import unidecode
import re


class TextNormalizer:
    """
    Class to preprocess transcripts of audio by removing unallowed chars and normalizing text.
    Allowed chars and chars to remove are defined in-class, in corresponding fields.
    For all chars which are not in the vocabulary we transform them in ASCII characters corresponding more or less
    to their sound (this is based on the unidecode_expect_ascii() function from 'unidecode' package).

    
    ***IMPORTANT***
    This class is supposed to be called in a Dataset.map Huggingface implementation. If you just want to normalize a single string, use
    the provided clas method normalize_text(string).

    ***NOTE***
    This was basically taken from TexPreProcessor here, relaxing the constraint given that whisper is very good with capitals and diacritcs: http://git.sinapsi.local/alessio.devoto/asr-it/-/blob/main/utils.py 
    """

    cfg = {
      'allowed_chars': [" ", "?", "!", ";", ":", '"', "'", 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'à', 'è', 'é', 'ì', 'ò', 'ù'],
      'chars_to_remove': [ '""', "�",'ʿ','“','”','(','=','`','_','+','«','<','>','~','…','«','»','–','\[','\]','°','´','ʾ','„','¡'], # ,'̇','̇','̇','̇',
      'apostrophe_to_remove':  ['̇', '̇', '̇', '̇', '`'],
      }

    def __init__(self):
        cfg = self.cfg
        self.chars_to_remove_regex = f"[{re.escape(''.join(cfg['chars_to_remove']))}]"
        self.allowed_chars = set(cfg['allowed_chars'])
        self.apostrophe_regex = f"[{re.escape(''.join(cfg['apostrophe_to_remove']))}]"

    def normalize_char(self, char):
        # Normalize unallowed chars to ASCII or corresponding sound.
        if char in self.allowed_chars:
            return char
        else:
            return unidecode.unidecode_expect_ascii(char)

    def normalize_text(self, sentence):
        # Remove unwanted characters and normalize chars one by one
        # print(self.chars_to_remove_regex)
        allowed_sentence = re.sub(self.apostrophe_regex, "'", sentence)
        allowed_sentence = re.sub(self.chars_to_remove_regex, '', allowed_sentence)
        new_sentence = ''
        for char in allowed_sentence:
            new_sentence += self.normalize_char(char)
        return new_sentence

    def __call__(self, batch):
        batch["sentence"] = self.normalize_text(batch["sentence"])
        return batch

def load_audio(filestorage, format=None, sample_rate=16000):
    torchaudio.set_audio_backend("sox_io")
    speech_array, original_sample_rate = torchaudio.load(filestorage, format=format)
    audio = resample(speech_array, original_sample_rate, sample_rate).squeeze()
    if audio.size()[0] == 2:
        audio = torch.mean(audio, dim=0).unsqueeze(0)
    return audio.squeeze()

def escape_html(s):
    """
    Escape unicode chars to html entities for italian vowels.
    """
    s = s.replace('è', '&egrave')
    s = s.replace('é', '&eacute')
    s = s.replace('à', '&agrave')
    s = s.replace('ì', '&igrave')
    s = s.replace('ò', '&ograve')
    s = s.replace('ù', '&ugrave')
    return s