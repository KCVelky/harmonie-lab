"""Lecture limitée d'un WAV de mesure, directement ou dans une archive ZIP."""
from contextlib import contextmanager
from fractions import Fraction
import io
import wave
import zipfile

import numpy as np
from scipy.signal import periodogram, resample_poly


MAX_WAV_BYTES = 200_000_000
MAX_SECONDS = 120
ANALYSIS_RATE = 400


@contextmanager
def open_wav(data, name):
    if name.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = [entry for entry in archive.infolist()
                       if entry.filename.lower().endswith('.wav') and not entry.is_dir()]
            if len(entries)!=1:
                raise ValueError('L’archive doit contenir un seul fichier WAV.')
            if entries[0].file_size>MAX_WAV_BYTES:
                raise ValueError('Le WAV décompressé dépasse 200 Mo.')
            with archive.open(entries[0]) as stream:
                with wave.open(stream, 'rb') as wav:
                    yield wav, entries[0].filename
    else:
        if not name.lower().endswith('.wav'):
            raise ValueError('Choisir un fichier WAV ou une archive ZIP contenant un WAV.')
        if len(data)>MAX_WAV_BYTES:
            raise ValueError('Le WAV dépasse 200 Mo.')
        with wave.open(io.BytesIO(data), 'rb') as wav:
            yield wav, name


def audio_info(data, name):
    try:
        with open_wav(data, name) as (wav, inner_name):
            if wav.getcomptype()!='NONE' or wav.getsampwidth() not in (1,2,3,4):
                raise ValueError('Seuls les WAV PCM de 8, 16, 24 ou 32 bits sont acceptés.')
            return dict(name=inner_name, channels=wav.getnchannels(),
                        sample_rate=wav.getframerate(), sample_width=wav.getsampwidth(),
                        duration=wav.getnframes()/wav.getframerate())
    except (wave.Error, zipfile.BadZipFile, EOFError) as exc:
        raise ValueError('Fichier audio illisible ou non pris en charge.') from exc


def decode_channel(raw, channels, sample_width, channel):
    if sample_width==1:
        samples=np.frombuffer(raw,dtype=np.uint8).reshape(-1,channels)[:,channel]
        return (samples.astype(np.float64)-128)/128
    if sample_width==2:
        samples=np.frombuffer(raw,dtype='<i2').reshape(-1,channels)[:,channel]
        return samples.astype(np.float64)/32768
    if sample_width==3:
        triplets=np.frombuffer(raw,dtype=np.uint8).reshape(-1,channels,3)[:,channel,:]
        value=(triplets[:,0].astype(np.int32)
               | triplets[:,1].astype(np.int32)<<8
               | triplets[:,2].astype(np.int32)<<16)
        return ((value ^ 0x800000)-0x800000).astype(np.float64)/8388608
    samples=np.frombuffer(raw,dtype='<i4').reshape(-1,channels)[:,channel]
    return samples.astype(np.float64)/2147483648


def spectrum(data, name, channel=0):
    info=audio_info(data,name)
    if not 0<=channel<info['channels']:
        raise ValueError('Canal absent du fichier.')
    if info['sample_rate']<2*150:
        raise ValueError('La fréquence d’échantillonnage est insuffisante pour 150 Hz.')
    sample_rate=info['sample_rate']
    ratio=Fraction(ANALYSIS_RATE,sample_rate).limit_denominator()
    frames_per_block=4*sample_rate
    frames_remaining=min(int(MAX_SECONDS*sample_rate),int(info['duration']*sample_rate))
    spectra=[]
    analyzed_frames=0
    try:
        with open_wav(data,name) as (wav,_):
            while frames_remaining>=2*sample_rate:
                request=min(frames_per_block,frames_remaining)
                raw=wav.readframes(request)
                if not raw:
                    break
                samples=decode_channel(raw,info['channels'],info['sample_width'],channel)
                if len(samples)<2*sample_rate:
                    break
                reduced=resample_poly(samples,ratio.numerator,ratio.denominator)
                f,p=periodogram(reduced,fs=sample_rate*ratio.numerator/ratio.denominator,
                                window='hann',detrend='constant',scaling='density',
                                nfft=4*ANALYSIS_RATE)
                spectra.append(p)
                analyzed_frames+=len(samples)
                frames_remaining-=len(samples)
    except (wave.Error, zipfile.BadZipFile, EOFError) as exc:
        raise ValueError('Lecture du WAV interrompue.') from exc
    if not spectra:
        raise ValueError('Il faut au moins deux secondes de signal.')
    power=np.mean(spectra,axis=0)
    return dict(info=info,channel=channel,frequency_hz=f,
                power=power,analyzed_seconds=analyzed_frames/sample_rate)


def band_power(result, target_hz, half_width=.5):
    frequencies=result['frequency_hz']; power=result['power']
    selected=np.abs(frequencies-target_hz)<=half_width
    if not np.any(selected):
        raise ValueError('Résolution spectrale insuffisante.')
    return float(np.mean(power[selected]))
