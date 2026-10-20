# Opening-hours review - 20 October 2026

The database contains 199 POIs. 38 schedules were checked against public web
references: 27 newly populated and 11 existing values confirmed or updated.
107 records now have nonempty hours, including one original `closed` record
excluded from recommendations. 92 records still have no confirmed schedule.
The remaining 69 original OSM values were not independently rechecked.

Canonical values, evidence URLs and dates are in
[manual_overrides.csv](../data/manual_overrides.csv).
The [review ledger](../data/hours_review.tsv) retains matched branch addresses
and qualifications. Overrides survive offline rebuilds. A reference check date
is not a statement that the owner updated the schedule on that date.

Sources include official venue websites (MEGA, Keruen, Ritz-Carlton, Ribambelle,
Astana museums, Ayashka and Veggie House), 2GIS cards considered during research,
Yandex Maps, Sxodim and other directories. Delivery hours are not visit hours.
Open-air locations were not automatically assigned 24/7 access.

## Unresolved and qualified cases

- Philharmonic and organ hall: visits depend on event schedules; ticket-office
  hours do not establish access to performances. See
  [Philharmonic](https://astana-filarmonia.kz/) and
  [Organ Hall](https://organhall.kz/).
- National Academic Library: weekly hours alone omit the maintenance day;
  a complete current access schedule was not established.
- Korme: tenant/office hours do not establish exhibition access.
- Flowerhub: a temporary closure notice requires further confirmation.
- Kultura Diktuet, Ma Famille, Segafredo and Rafe at Konaev 12/2:
  references disagree about opening, closing or weekend hours.
- University parks/gardens: public unrestricted access was not established.
  Other outdoor locations without explicit published hours also stay unknown.
- Veggie House: the site's general header says 22:00, but the branch section
  and footer both say 21:00. The explicit branch schedule 10:00-21:00 is used.
- Sazan at Kenesary 24: the card matched by address and coordinates now uses
  the name FSN. Hours were not transferred to Sazan because the identity of
  the organization is uncertain; this needs a separate name review.

## Records without confirmed hours

This is the complete gap list, not a claim that each location was verified
with its owner. Unknown hours never imply that the venue is open.

| POI | Category | ID |
| --- | --- | --- |
| [Artist](https://www.openstreetmap.org/node/12973428159) | arts_centre | `osm:node:12973428159` |
| [Е. Рахмадиев атындағы Мемлекеттік академиялық филармония](https://www.openstreetmap.org/node/4916363251) | arts_centre | `osm:node:4916363251` |
| [Органный зал Национальной академии музыки РК](https://www.openstreetmap.org/node/3824846563) | arts_centre | `osm:node:3824846563` |
| [А. Құнанбайұлы](https://www.openstreetmap.org/node/3743119878) | attraction | `osm:node:3743119878` |
| [Айтеке-би, Казыбек-би и Толе-би](https://www.openstreetmap.org/node/4109068594) | attraction | `osm:node:4109068594` |
| [Атырау көпірі](https://www.openstreetmap.org/way/1239177393) | attraction | `osm:way:1239177393` |
| [М. Мәметова](https://www.openstreetmap.org/node/7142226485) | attraction | `osm:node:7142226485` |
| [Мемориал Великой Отечественной войны](https://www.openstreetmap.org/node/7149180388) | attraction | `osm:node:7149180388` |
| [Памятник "Жанибек и Керей хандары"](https://www.openstreetmap.org/node/2712544129) | attraction | `osm:node:2712544129` |
| [Памятник Богенбай Батыру](https://www.openstreetmap.org/way/384145918) | attraction | `osm:way:384145918` |
| [Памятник жертвам голодомора](https://www.openstreetmap.org/node/4113550330) | attraction | `osm:node:4113550330` |
| [С. Сейфуллин](https://www.openstreetmap.org/node/2349679958) | attraction | `osm:node:2349679958` |
| [Тәуелсіздіктің 25 жылдығы](https://www.openstreetmap.org/way/1460763574) | attraction | `osm:way:1460763574` |
| [#Забери с собой](https://www.openstreetmap.org/node/12917106648) | cafe | `osm:node:12917106648` |
| [Amore Mio](https://www.openstreetmap.org/node/5077232622) | cafe | `osm:node:5077232622` |
| [Asia mix](https://www.openstreetmap.org/node/12947062984) | cafe | `osm:node:12947062984` |
| [Basqur](https://www.openstreetmap.org/node/12973424137) | cafe | `osm:node:12973424137` |
| [Baton coffee](https://www.openstreetmap.org/node/12917088083) | cafe | `osm:node:12917088083` |
| [Cafe](https://www.openstreetmap.org/node/13408518301) | cafe | `osm:node:13408518301` |
| [Central pizza & coffee](https://www.openstreetmap.org/node/12146103478) | cafe | `osm:node:12146103478` |
| [Chaleur](https://www.openstreetmap.org/node/10170946745) | cafe | `osm:node:10170946745` |
| [Coffee Decaf](https://www.openstreetmap.org/node/12993958970) | cafe | `osm:node:12993958970` |
| [Coffee Stories](https://www.openstreetmap.org/node/12973394495) | cafe | `osm:node:12973394495` |
| [Coffee Stories](https://www.openstreetmap.org/node/12990081601) | cafe | `osm:node:12990081601` |
| [Coffee Way](https://www.openstreetmap.org/node/12896611717) | cafe | `osm:node:12896611717` |
| [Drinkit](https://www.openstreetmap.org/node/14100100182) | cafe | `osm:node:14100100182` |
| [Durum](https://www.openstreetmap.org/node/12896623405) | cafe | `osm:node:12896623405` |
| [Espresso Bar](https://www.openstreetmap.org/node/5074875221) | cafe | `osm:node:5074875221` |
| [EzHub](https://www.openstreetmap.org/node/12917107318) | cafe | `osm:node:12917107318` |
| [Global Coffee](https://www.openstreetmap.org/node/12973419508) | cafe | `osm:node:12973419508` |
| [HamStar](https://www.openstreetmap.org/node/4792472508) | cafe | `osm:node:4792472508` |
| [Im](https://www.openstreetmap.org/way/1342224679) | cafe | `osm:way:1342224679` |
| [Kunde Cafe](https://www.openstreetmap.org/node/13462282540) | cafe | `osm:node:13462282540` |
| [La Belle](https://www.openstreetmap.org/node/12896579454) | cafe | `osm:node:12896579454` |
| [LatTea](https://www.openstreetmap.org/node/12973421415) | cafe | `osm:node:12973421415` |
| [Ma Famille French Cafe](https://www.openstreetmap.org/node/12876977238) | cafe | `osm:node:12876977238` |
| [Mado](https://www.openstreetmap.org/node/6404769888) | cafe | `osm:node:6404769888` |
| [Moment coffee](https://www.openstreetmap.org/node/12135824881) | cafe | `osm:node:12135824881` |
| [PizBurg](https://www.openstreetmap.org/node/12135832778) | cafe | `osm:node:12135832778` |
| [Qazaq coffee](https://www.openstreetmap.org/node/12095545748) | cafe | `osm:node:12095545748` |
| [Rafe](https://www.openstreetmap.org/node/4133854089) | cafe | `osm:node:4133854089` |
| [Sazan](https://www.openstreetmap.org/node/12135831824) | cafe | `osm:node:12135831824` |
| [Segafredo](https://www.openstreetmap.org/node/12747390104) | cafe | `osm:node:12747390104` |
| [Tagam](https://www.openstreetmap.org/node/12993953677) | cafe | `osm:node:12993953677` |
| [Tez besh](https://www.openstreetmap.org/node/12146103477) | cafe | `osm:node:12146103477` |
| [Vanil' Coffee](https://www.openstreetmap.org/node/12896556565) | cafe | `osm:node:12896556565` |
| [Zefir coffee](https://www.openstreetmap.org/node/12093501445) | cafe | `osm:node:12093501445` |
| [marrone rosso](https://www.openstreetmap.org/node/11910202470) | cafe | `osm:node:11910202470` |
| [Дружба](https://www.openstreetmap.org/node/12917093975) | cafe | `osm:node:12917093975` |
| [Кафела](https://www.openstreetmap.org/node/5936638686) | cafe | `osm:node:5936638686` |
| [Культура Диктует](https://www.openstreetmap.org/node/12959449801) | cafe | `osm:node:12959449801` |
| [Пекарня Мишеля](https://www.openstreetmap.org/node/4207115191) | cafe | `osm:node:4207115191` |
| [Рыба моей мечты](https://www.openstreetmap.org/node/4499897795) | cafe | `osm:node:4499897795` |
| [Сладкая Сказка](https://www.openstreetmap.org/node/5244218857) | cafe | `osm:node:5244218857` |
| [Тамсан](https://www.openstreetmap.org/way/158630906) | cafe | `osm:way:158630906` |
| [Точка](https://www.openstreetmap.org/node/12917106289) | cafe | `osm:node:12917106289` |
| [завтрак бар](https://www.openstreetmap.org/node/6408255389) | cafe | `osm:node:6408255389` |
| [Көрме](https://www.openstreetmap.org/way/230358847) | gallery | `osm:way:230358847` |
| [Японский сад](https://www.openstreetmap.org/way/1470723968) | garden | `osm:way:1470723968` |
| [Қазақстан Республикасының Ұлттық академиялық кітапханасы](https://www.openstreetmap.org/way/230358855) | library | `osm:way:230358855` |
| [Flowerhub](https://www.openstreetmap.org/way/264403130) | mall | `osm:way:264403130` |
| [ҚР Тұңғыш Президенті Н. Ә. Назарбаевтың мұражайы](https://www.openstreetmap.org/way/51431624) | museum | `osm:way:51431624` |
| [NU Park](https://www.openstreetmap.org/way/1467797207) | park | `osm:way:1467797207` |
| [Арай саябағы](https://www.openstreetmap.org/way/243041609) | park | `osm:way:243041609` |
| [Бейбітшілік пен Келісім аллеясы](https://www.openstreetmap.org/way/1456208624) | park | `osm:way:1456208624` |
| [Гүл бақшасы](https://www.openstreetmap.org/relation/3573848) | park | `osm:relation:3573848` |
| [Жастар сарайы алаңы](https://www.openstreetmap.org/way/1428964223) | park | `osm:way:1428964223` |
| [Сквер](https://www.openstreetmap.org/way/230358854) | park | `osm:way:230358854` |
| [Сквер шахматистов](https://www.openstreetmap.org/way/262166875) | park | `osm:way:262166875` |
| [Тұңғыш Президент мұражайының алаңы](https://www.openstreetmap.org/way/1428966977) | park | `osm:way:1428966977` |
| [Astana-Nury](https://www.openstreetmap.org/node/4922406025) | restaurant | `osm:node:4922406025` |
| [Authentica Roni Napoletana](https://www.openstreetmap.org/node/10171023214) | restaurant | `osm:node:10171023214` |
| [Bekbota](https://www.openstreetmap.org/node/10171023216) | restaurant | `osm:node:10171023216` |
| [Coffee Bus Expresso Luxury](https://www.openstreetmap.org/node/10171023213) | restaurant | `osm:node:10171023213` |
| [Fuller's Pub](https://www.openstreetmap.org/node/5890174288) | restaurant | `osm:node:5890174288` |
| [Lugano](https://www.openstreetmap.org/node/5966393585) | restaurant | `osm:node:5966393585` |
| [Peek-a-boo](https://www.openstreetmap.org/node/14100100183) | restaurant | `osm:node:14100100183` |
| [Pivovaroff](https://www.openstreetmap.org/node/10171023215) | restaurant | `osm:node:10171023215` |
| [The Kitchen](https://www.openstreetmap.org/node/4384857439) | restaurant | `osm:node:4384857439` |
| [Yakitoriya](https://www.openstreetmap.org/node/10168258158) | restaurant | `osm:node:10168258158` |
| [Yessil](https://www.openstreetmap.org/node/12993941023) | restaurant | `osm:node:12993941023` |
| [Z-1](https://www.openstreetmap.org/node/6312771198) | restaurant | `osm:node:6312771198` |
| [ocean basket](https://www.openstreetmap.org/node/6404773385) | restaurant | `osm:node:6404773385` |
| [Арай](https://www.openstreetmap.org/node/4915119663) | restaurant | `osm:node:4915119663` |
| [Асату](https://www.openstreetmap.org/node/12973410493) | restaurant | `osm:node:12973410493` |
| [Бистро Коктем](https://www.openstreetmap.org/node/4624217690) | restaurant | `osm:node:4624217690` |
| [Демалыс](https://www.openstreetmap.org/node/5866018459) | restaurant | `osm:node:5866018459` |
| [Жагалау](https://www.openstreetmap.org/node/5889814892) | restaurant | `osm:node:5889814892` |
| [Меруерт](https://www.openstreetmap.org/node/4913160607) | restaurant | `osm:node:4913160607` |
| [Мост](https://www.openstreetmap.org/node/5936655589) | restaurant | `osm:node:5936655589` |
| [Саксаул](https://www.openstreetmap.org/node/4953253121) | restaurant | `osm:node:4953253121` |
| [Фархи](https://www.openstreetmap.org/node/1843876240) | restaurant | `osm:node:1843876240` |
