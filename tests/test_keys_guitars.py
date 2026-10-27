"""Fixed sample programs must select one playing mode without silently discarding features."""
import pytest

from songmap.parse.errors import SongError


def test_fixed_program_filters_pedal_keyswitch_and_channel(tmp_path):
    from songmap.instruments.sampler.curate import prepare
    from songmap.instruments.sampler.sfz import parse
    source = tmp_path/'source.sfz'
    source.write_text('''<global> amp_random=1 pitch_random=4 off_mode=normal
<group> lochan=1 hichan=1 sw_last=25 locc64=0 hicc64=64
<region> sample=good.wav key=60
<group> lochan=1 hichan=1 sw_last=26
<region> sample=wrong_style.wav key=60
<group> lochan=2 hichan=2 sw_last=25
<region> sample=wrong_channel.wav key=60
<group> lochan=1 hichan=1 sw_last=25 locc64=65
<region> sample=wrong_pedal.wav key=60
<group> on_locc64=0 on_hicc64=64
<region> sample=pedal_event.wav key=60
''')
    target=tmp_path/'prepared'/'voice.sfz'
    profile={'cc':{'64':0},'keyswitch':25,'channel':1,'drop':['amp_random','pitch_random'],
             'set':{'off_mode':'fast'}}
    prepare(source,target,profile)
    p=parse(str(target))
    assert not p.unsupported and len(p.regions)==1
    assert p.regions[0].sample==str(tmp_path/'good.wav')
    assert source.read_text().startswith('<global> amp_random=1')


def test_fixed_program_rejects_unreviewed_features(tmp_path):
    from songmap.instruments.sampler.curate import prepare
    p=tmp_path/'source.sfz';p.write_text('<region> sample=tone.wav cutoff=300 key=60')
    with pytest.raises(SongError,match='cutoff'):
        prepare(p,tmp_path/'target.sfz',{})


def test_installer_prepared_voice_is_verified_and_resumable(tmp_path,monkeypatch):
    import json
    from songmap.instruments.sampler import install as installer,library,sfz
    files={'voice.sfz':b'<group> locc64=0 hicc64=64\n<region> sample=audio/good.wav key=60\n<group> locc64=65\n<region> sample=audio/bad.wav key=60',
           'audio/good.wav':b'good sample fixture','LICENSE':b'CC0'}
    source={'repo':'test/keys','revision':'a'*40,'license':'CC0','credit':'Fixture','url':'https://example.com'}
    voice={'title':'Fixture','source':'keys','program':'voice.sfz','family':'keys','description':'Test','range':[60,60],'adapt':{'cc':{'64':0}}}
    monkeypatch.setattr(library,'manifest',lambda:{'sources':{'keys':source},'voices':{'piano':voice}})
    tree={'tree':[{'path':k,'type':'blob','sha':installer._blob(v),'size':len(v)} for k,v in files.items()]}
    def read(url):
        if 'api.github' in url:return json.dumps(tree).encode()
        return files[url.split(source['revision']+'/')[1]]
    monkeypatch.setattr(installer,'_read',read)
    installer.install(['piano'],root=tmp_path/'samples',log=lambda _:None)
    prepared=library.voice_path(tmp_path/'samples','piano')
    assert prepared != tmp_path/'samples/_packs/keys/voice.sfz'
    assert sfz.parse(str(prepared)).regions[0].sample.replace('\\','/').endswith('audio/good.wav')
    assert installer.verify(tmp_path/'samples')['ok']
    assert (tmp_path/'samples/_packs/keys/voice.sfz').read_bytes()==files['voice.sfz']
    prepared.write_text('corrupted')
    assert not installer.verify(tmp_path/'samples')['ok']
    installer.install(['piano'],root=tmp_path/'samples',log=lambda _:None)
    assert installer.verify(tmp_path/'samples')['ok']


def test_keyboard_and_guitar_catalog_is_shared_with_studio_and_ai():
    from songmap.describe import catalog
    from songmap.gui.rack import catalog as studio_catalog
    cat=studio_catalog()
    samples={v['name']:v for v in cat['samplers']}
    for name in ('steinway_piano','knight_piano','meta_piano','rhodes_mono','nylon_finger','nylon_pick','steel_guitar','archtop_mic','emily_clean'):
        assert samples[name]['description'] and samples[name]['category']
        assert 'sampler/'+name in catalog(compact=True)
    assert len([v for v in samples.values() if v['category']=='Acoustic pianos'])==5
    assert len([p for p in cat['presets']['epiano'] if 'keys-guitar-palette' in p['tags']])==8


def test_prepared_program_credits_point_to_the_actual_source_pack(tmp_path,monkeypatch):
    from songmap.instruments.sampler import library
    voice={'source':'fixture','program':'some/deep/source.sfz','adapt':{},'title':'Test'}
    monkeypatch.setattr(library,'manifest',lambda:{'voices':{'test':voice},'sources':{'fixture':{'license':'CC0','url':'https://example.com','credit':'Test'}}})
    pack=tmp_path/'_packs/fixture';(pack/'_songmap').mkdir(parents=True)
    (pack/'LICENSE').write_text('Test CC0')
    entry=library.license_entry('test',str(pack/'_songmap/test.sfz'))
    assert entry['files']==[str(pack/'LICENSE')]


def test_compact_sample_brace_choices_recover_every_reference():
    import re
    from songmap.describe import catalog
    from songmap.instruments.sampler.library import manifest
    line=next(l for l in catalog().splitlines() if l.startswith('sfz '))
    refs=[]
    for token in line.split()[1:]:
        m=re.fullmatch(r'(sampler/[^{}]*)\{([^}]+)\}',token)
        refs.extend([m[1]+s for s in m[2].split(',')] if m else [token])
    assert set(refs)=={'sampler/'+n for n in manifest()['voices']}
