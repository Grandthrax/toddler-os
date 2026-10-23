import argparse
"""Natural page speech and contextual word clips for the picture storybook."""
from array import array
from pathlib import Path
from types import SimpleNamespace
import hashlib
import io
import json
import re
import sys
import wave

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'app'))
from core import Speech, word_timings
from storybooks import prompts

RECIPE=2
NAME_PRONUNCIATIONS = {}


def spoken_text(text):
    return text


def render_prompt(speech,text):
    if spoken_text(text)==text:return speech.render(text)
    if speech.voice is None:speech.render('hello')
    chunks=list(speech.voice.synthesize(spoken_text(text),include_alignments=True))
    return wav_bytes(b''.join(chunk.audio_int16_bytes for chunk in chunks)),word_timings(text,chunks)


def wav_bytes(frames, rate=22050):
    output=io.BytesIO()
    with wave.open(output,'wb') as destination:
        destination.setparams((1,2,rate,0,'NONE','not compressed'))
        destination.writeframes(frames)
    return output.getvalue()


def natural_page(speech, text):
    audio,timings=render_prompt(speech,text)
    if timings:return audio,timings
    # eSpeak joins "on the" and "was the" as phoneme groups. Split their
    # measured consonant/eth boundaries without changing the sentence audio.
    chunks=list(speech.voice.synthesize(spoken_text(text),include_alignments=True))
    aligned=[];splits=0
    for chunk in chunks:
        phonemes=[];previous=None
        for item in chunk.phoneme_alignments:
            if item.phoneme=='\u00f0' and (('on the' in text.lower() and previous=='n') or ('was the' in text.lower() and previous=='z')):
                phonemes.append(SimpleNamespace(phoneme=' ',num_samples=0));splits+=1
            phonemes.append(item);previous=item.phoneme
        aligned.append(SimpleNamespace(phoneme_alignments=phonemes,sample_rate=chunk.sample_rate,
            sample_width=chunk.sample_width,sample_channels=chunk.sample_channels,audio_int16_bytes=chunk.audio_int16_bytes))
    timings=word_timings(text,aligned)
    if not timings or splits!=1:raise RuntimeError('Review natural page alignment: '+text)
    assert all(chunk.sample_rate==22050 and chunk.sample_channels==1 and chunk.sample_width==2 for chunk in chunks)
    return wav_bytes(b''.join(chunk.audio_int16_bytes for chunk in chunks)),timings


def contextual_word(folder, pages, word):
    candidates=[]
    for name,entry in pages.items():
        for index,boundary in enumerate(entry['words']):
            if entry['text'][boundary[0]:boundary[1]].lower()==word:
                candidates.append((boundary[3]-boundary[2],name,index))
    if not candidates:raise RuntimeError('No spoken sentence contains '+word)
    _,name,index=max(candidates)
    entry=pages[name];boundaries=entry['words'];start,end=boundaries[index][2:]
    with wave.open(str(folder/(name+'.wav'))) as source:
        rate=source.getframerate();total=source.getnframes();frames=source.readframes(total)
    previous_end=boundaries[index-1][3]+.01 if index else 0
    next_start=boundaries[index+1][2]-.01 if index+1<len(boundaries) else total/rate
    first=max(0,int(max(previous_end,start-.045)*rate))
    last=min(total,int(min(next_start,end+.055)*rate))
    samples=array('h');samples.frombytes(frames[first*2:last*2])
    if sys.byteorder!='little':samples.byteswap()
    # Tiny edge fades avoid clicks. Preserve the recorded phonemes and pitch.
    fade=min(int(rate*.004),len(samples)//2)
    for n in range(fade):
        gain=n/fade;samples[n]=int(samples[n]*gain);samples[-1-n]=int(samples[-1-n]*gain)
    if sys.byteorder!='little':samples.byteswap()
    lead=int(rate*.06);tail=int(rate*.08)
    audio=wav_bytes(b'\x00\x00'*lead+samples.tobytes()+b'\x00\x00'*tail,rate)
    timings=[[0,len(word),round(lead/rate+start-first/rate,5),round(lead/rate+end-first/rate,5)]]
    return audio,timings,{'source_page':name,'source_word':index,'source_samples':[first,last]}


def main():
    folder=HERE/'app/static/storybooks/audio';folder.mkdir(parents=True,exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    speech = Speech(parser.parse_args().model)
    old=json.loads((folder/'manifest.json').read_text())['prompts'] if (folder/'manifest.json').exists() else {}
    manifest={};text_by_name=prompts()
    for key,text in text_by_name.items():
        if key.startswith('word-'):continue
        file=folder/(key+'.wav');entry=old.get(key,{})
        pronunciation={word:ipa for word,ipa in NAME_PRONUNCIATIONS.items() if re.search(r'\b'+word+r'\b',text,re.I)}
        if pronunciation and entry.get('pronunciations')!=pronunciation:entry={}
        if entry.get('text')==text and file.exists() and (not key.startswith('page-') or entry.get('recipe')==RECIPE):
            manifest[key]=entry;continue
        audio,timings=natural_page(speech,text) if key.startswith('page-') else render_prompt(speech,text)
        file.write_bytes(audio)
        manifest[key]={'text':text,'sha256':hashlib.sha256(audio).hexdigest(),'words':timings,'recipe':RECIPE,
                       **({'pronunciations':pronunciation} if pronunciation else {})}
        print(key,len(audio),flush=True)
    pages={name:entry for name,entry in manifest.items() if name.startswith('page-')}
    for key,text in text_by_name.items():
        if not key.startswith('word-'):continue
        entry=old.get(key,{})
        # Preserve the reviewed Space Cat word recordings. New vocabulary is
        # extracted from continuous sentences, including the pronounced name.
        if entry.get('text')==text and entry.get('recipe')==RECIPE and (folder/(key+'.wav')).exists() and text not in NAME_PRONUNCIATIONS:
            manifest[key]=entry;continue
        audio,timings,provenance=contextual_word(folder,pages,text)
        (folder/(key+'.wav')).write_bytes(audio)
        manifest[key]={'text':text,'sha256':hashlib.sha256(audio).hexdigest(),'words':timings,'recipe':RECIPE,**provenance,
                       **({'pronunciations':{text:NAME_PRONUNCIATIONS[text]}} if text in NAME_PRONUNCIATIONS else {})}
        print(key,len(audio),provenance['source_page'],flush=True)
    (folder/'manifest.json').write_text(json.dumps({'voice':'en_GB-cori-high','prompts':manifest},indent=2)+'\n')


if __name__=='__main__':main()
