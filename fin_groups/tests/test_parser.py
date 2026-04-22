# test_parser.py
from fin_groups.parser import parse_owners, parse_company_metadata

sample_html = """<section class="bg-body rounded p-3 mb-2"><hgroup><h3>Реєстраційні дані</h3></hgroup>
<div class="reset-margin-b"><dl class="row g-2" itemscope="itemscope" itemtype="https://schema.org/Organization">
<div class="col col-6 col-md-4"><dt class="fw-normal text-body-tertiary">Директор</dt>
<dd class="user-select-all" data-odb-prop="employee">
<a href="/p/fedorenko-antonina-mykolayivna-9I-HvONr1fpZ39e35VG3CA">Федоренко Антоніна Миколаївна</a></dd></div>
</dl>
<dl class="row g-2 mb-2"><dt class="col-12 text-body-tertiary fw-normal mb-0">Керівники</dt>
<dd class="col-6 col-md-4 col-xl-3 print-responsive"><p class="mb-1">Федоренко Антоніна Миколаївна</p>
<p class="mb-1 small">керівник</p><p class="mb-1 small"></p></dd>
<dd class="col-6 col-md-4 col-xl-3 print-responsive"><p class="mb-1">Федоренко Антоніна Миколаївна</p>
<p class="mb-1 small">підписант</p><p class="mb-1 small"></p></dd></dl>
<dl class="row g-2 mb-2"><dt class="col-12 text-body-tertiary fw-normal mb-0">Власники</dt>
<dd class="col-6 col-md-4 col-xl-3 print-responsive"><p class="mb-1">Акціонери</p>
<p class="mb-1 small">Засновник</p><data class="mb-1 small" value="1225771"> 1&nbsp;225&nbsp;771&nbsp;₴<span><svg class="svg-pie text-primary"></svg>100%</span></data></dd></dl></section>"""

metadata_html = """<section class="bg-body rounded p-3 mb-2"><hgroup><h3>Реєстраційні дані</h3></hgroup>
<dl class="row g-2" itemscope="itemscope" itemtype="https://schema.org/Organization">
<div class="col col-12"><dt class="fw-normal text-body-tertiary"><meta itemprop="name" content="ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ - ПІДПРИЄМСТВО  «АВІС»">Повна назва</dt>
<dd class="user-select-all" data-odb-prop="name"><p class="mb-0">ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ - ПІДПРИЄМСТВО  «АВІС»</p></dd></div>
<div class="col col-12"><dt class="fw-normal text-body-tertiary">Адреса</dt>
<dd class="user-select-all" data-odb-prop="address"><p>21037, Україна, Вінницький р-н, Вінницька обл., місто Вінниця, вулиця Пирогова, будинок 150</p></dd></div>
<div class="col col-6 col-md-4"><dt class="fw-normal text-body-tertiary">Дата заснування</dt>
<dd class="user-select-all" data-odb-prop="foundingDate"><time datetime="1998-07-21">21.07.1998</time></dd></div>
</dl>
<div class="alert border-0 mb-2 alert-danger"><span><span>Статус компанії: в стані припинення</span></span></div>"""


def test_parse_owners_basic():
    people = parse_owners(sample_html, is_html=True)

    # Check that we got all people (owners + director + managers)
    assert len(people) == 4  # adjust if your HTML has 4 people total

    # Check director
    director = [p for p in people if p["role"] == "director"][0]
    assert director["share_percent"] == 0.0
    assert director["amount_uah"] is None
    assert "Федоренко" in director["name"]

    # Check owner
    owner = [p for p in people if p["role"] == "Засновник" or p["role"] == "owner"][0]
    assert owner["share_percent"] == 100.0
    assert owner["amount_uah"] == 1225771


def test_parse_company_metadata():
    metadata = parse_company_metadata(metadata_html, is_html=True)

    assert metadata["name"] == "ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ - ПІДПРИЄМСТВО  «АВІС»"
    assert metadata["address"].startswith("21037, Україна")
    assert metadata["founding_date"] == "1998-07-21"
    assert metadata["status"] == "в стані припинення"
