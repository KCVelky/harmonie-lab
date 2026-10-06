from dataclasses import replace
import io
import wave
import zipfile

import numpy as np

from analyse_t12 import audio_info, band_power, spectrum
from etude_sandra import compare_positions, reference_string, summarize_comparison
from physics import Plate, Support, string_frequencies


def museum_plate():
    return Plate(H=2.4384,W=1.524,h=.003175,rho=650.,Es=10e9,Eu=10e9,
                 G=10e9/2.6,nu=.30,boundary='Appuis simples',bridge_s=2.19456,
                 bridge_mass=.010,damping=.012,order=6)


def test_reference_string_and_comparison():
    wire=reference_string()
    np.testing.assert_allclose(wire.T,206.49,atol=.02)
    np.testing.assert_allclose(string_frequencies(wire,7)[[4,6]],[60,84],atol=.01)
    assert wire.gain2==0 and wire.p1==.10
    timber=Support(enabled=True,width=.0381,depth=.0381,rho=500.,E=10e9)
    rows=compare_positions(museum_plate(),wire,timber)
    assert len(rows)==12
    summary=summarize_comparison(rows)
    assert all(row['stable'] for row in summary)
    assert summary[0]['rms_22_5']>summary[0]['rms_10']
    assert summary[0]['ratio_10_over_22_5']<.7
    assert .75<summary[1]['ratio_10_over_22_5']<1.1
    changed=compare_positions(museum_plate(),replace(wire,beta=.10),timber,
                              orders=(12,14))
    assert len(changed)==8


def test_t12_style_zip_and_spectrum():
    rate=400
    t=np.arange(4*rate)/rate
    channels=np.zeros((len(t),4),dtype=np.int32)
    channels[:,0]=np.round((.5*np.sin(2*np.pi*60*t)
                            +.05*np.sin(2*np.pi*84*t))*8388607).astype(np.int32)
    unsigned=channels & 0xffffff
    raw=np.stack([unsigned&255,(unsigned>>8)&255,(unsigned>>16)&255],axis=-1)
    wav_buffer=io.BytesIO()
    with wave.open(wav_buffer,'wb') as wav:
        wav.setnchannels(4);wav.setsampwidth(3);wav.setframerate(rate)
        wav.writeframes(raw.astype(np.uint8).tobytes())
    zip_buffer=io.BytesIO()
    with zipfile.ZipFile(zip_buffer,'w') as archive:
        archive.writestr('T12_poutre acier.WAV',wav_buffer.getvalue())
        archive.writestr('figure.png',b'figure')
    payload=zip_buffer.getvalue()
    info=audio_info(payload,'t12.zip')
    assert info['channels']==4 and info['duration']==4
    result=spectrum(payload,'t12.zip',0)
    assert band_power(result,60)>50*band_power(result,84)
    silent=spectrum(payload,'t12.zip',1)
    assert np.max(silent['power'])==0
