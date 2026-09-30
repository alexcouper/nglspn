import { guides, type Guide } from "./guides";

// Slugs and section anchors are shared so language switches retain the topic.
type Translation = Pick<Guide, "title" | "description" | "summary" | "action"> & {
  sections: { title: string; body: string }[];
};

const translations: Record<string, Translation> = {
  "iceland-developer-community": {
    title: "Hvað er Naglasúpan? Hugbúnaðarsamfélag á Íslandi",
    description: "Naglasúpan tengir saman fólk sem smíðar hugbúnað á Íslandi. Kynntu þér íslensk hliðarverkefni, söguna á bak við nafnið og leiðir til að taka þátt.",
    summary: "Naglasúpan er samfélagsvettvangur fyrir fólk sem smíðar hugbúnað á Íslandi. Hér getur þú kynnt þér íslensk hliðarverkefni, deilt eigin verkum og skipst á ábendingum við aðra. Þú getur tekið þátt með því að prófa verkefni, spyrja gagnlegrar spurningar eða bjóða fram afmarkaða aðstoð.",
    action: { href: "/projects", label: "Skoða verkefnin" },
    sections: [
      {
        title: "„Nagla súpa“ og sagan á bak við Naglasúpuna",
        body: "Nafnið Naglasúpan vísar í söguna um naglasúpu. Ferðalangur byrjar að sjóða súpu úr nokkrum nöglum. Forvitnir þorpsbúar leggja hver sitt hráefni í pottinn og að lokum verður úr sameiginleg máltíð. Útgáfuna sem veitti verkefninu innblástur má lesa í [kynningu Naglasúpunnar](https://github.com/alexcouper/nglspn#the-story-brief-mode).\n\nSama hugmynd liggur að baki þessu hugbúnaðarsamfélagi á Íslandi. Einn kemur með hliðarverkefni, annar prófar það og gefur ábendingar og sá þriðji býður fram færni sína. Framlag þarf ekki að vera stórt til að hjálpa verkefni áfram.\n\nÁ naglasupan.is vinnur samfélagið að hugbúnaði: [öppum, verkfærum og tilraunaverkefnum](/projects). Byrjaðu á verkefni sem vekur áhuga þinn eða lestu [leiðarvísinn um þátttöku](/guides/iceland-developer-community/get-involved) til að finna fyrsta skrefið þitt.",
      },
      {
        title: "Hvar finnur þú það sem fólk á Íslandi er að smíða?",
        body: "[Verkefnaskráin](/projects) er upphafspunkturinn á Naglasúpunni. Skoðaðu verkefnin, opnaðu eitthvað sem vekur áhuga þinn og lestu lýsingu höfundarins. Prufuútgáfa, skjámynd og nýleg færsla segja þér ólíka hluti: hvað þú getur prófað, hvernig það lítur út og hvað hefur breyst.\n\nNaglasúpan leggur áherslu á það sem fólk er að búa til og deila. Til að fá víðara sjónarhorn á sprotaumhverfið má skoða [Northstack](https://www.northstack.is/about/), sem lýsir þar fréttaflutningi sínum og samfélagsstarfi. Þetta eru ólíkar leiðir inn í íslenskt tæknisamfélag; hvorug gefur tæmandi mynd af öllu sem hér er unnið að.\n\nÍ [leiðarvísinum um að finna íslensk hugbúnaðarverkefni](/guides/iceland-developer-community/find-projects) færðu aðstoð við að velja nokkur verkefni til að prófa.",
      },
      {
        title: "Veldu hvernig þú vilt taka þátt",
        body: "Þú þarft ekki að vera með fullbúið forrit til að leggja eitthvað gagnlegt af mörkum. Veldu aðgerð sem hentar því sem þú hefur fram að færa:\n\n- **Forvitni:** prófaðu verkefni og lýstu því sem þú bjóst við að myndi gerast.\n- **Eigið verkefni:** útskýrðu fyrir hverja það er, sýndu stöðuna og spurðu einnar afmarkaðrar spurningar.\n- **Færni:** bjóddu fram afmarkaða aðstoð, svo sem að bæta uppsetningarleiðbeiningar eða prófa síðu í síma.\n- **Áhugaverð uppgötvun:** bentu á verkefni annarra og láttu skýrt koma fram hver bjó það til.\n\nSjáðu dæmi um kynningu í [leiðarvísinum um þátttöku](/guides/iceland-developer-community/get-involved). Ef þú ert tilbúin eða tilbúinn að sýna eigin verk skaltu skoða [leiðarvísinn um að deila hliðarverkefni](/guides/share-a-side-project).",
      },
      {
        title: "Hvað getur þú gert á Naglasúpunni?",
        body: "Á Naglasúpunni fá verkefni opinbera síðu og umræðusvæði. Höfundar geta lýst verkum sínum og birt greinar um þau, og áhugasamt fólk getur fylgst með verkefnum. Samfélagskeppnir eru önnur leið til þátttöku; nánari upplýsingar eru á hverri [keppnissíðu](/competitions).\n\nAð stofna drög, senda verkefni til birtingar og skrá það í keppni eru aðskilin skref. Verkefni sem sent er til birtingar fer í yfirferð. Það birtist ekki strax opinberlega og skráist ekki sjálfkrafa í keppni. Farðu yfir [gátlistann fyrir verkefnasíðu](/guides/share-a-side-project/project-page-checklist) áður en þú sendir það inn.\n\nLangtímamarkmiðin fela meðal annars í sér aukið samstarf og sameiginlega innviði. [Tilgangur verkefnisins](/about/why) lýsir þeirri stefnu, en er ekki upptalning á þjónustu sem þegar er í boði.",
      },
      {
        title: "Gerðu fyrstu samskiptin gagnleg",
        body: "Veldu eitt verkefni, gefðu þér nokkrar mínútur til að skilja tilgang þess og skrifaðu skilaboð sem tengjast einhverju sem þú prófaðir. Ábending á borð við „Ég fann kortið en sá ekki hvernig ég gæti bætt við merki í símanum“ gefur höfundi eitthvað áþreifanlegt til að skoða.\n\nÞegar þú kemur aftur skaltu athuga hvort höfundurinn hafi svarað eða birt nýja færslu. Samtal sem heldur áfram getur verið gagnlegra en að kynna sig fyrir mörgum í einu. [Leiðarvísirinn um framlög](/guides/contribute-to-projects) sýnir hvernig fyrstu samskiptin geta orðið að viðráðanlegu verkefni.",
      },
    ],
  },
  "iceland-developer-community/find-projects": {
    title: "Hvernig finnur þú íslensk hugbúnaðar- og hliðarverkefni?",
    description: "Finndu íslensk hugbúnaðarverkefni út frá vandanum sem þau leysa, kannaðu hvað er hægt að prófa og fylgstu með því sem vekur áhuga þinn.",
    summary: "Leitaðu að vanda sem þú þekkir og skoðaðu síðan verkefnalýsingu, prufuútgáfu og uppfærslur. Verkefnaskrá Naglasúpunnar er upphafspunktur til að finna hugbúnað úr íslensku samfélagi skapandi tæknifólks, allt frá fyrstu tilraunum til verkfæra í notkun.",
    action: { href: "/projects", label: "Finna verkefni til að prófa" },
    sections: [
      {
        title: "Byrjaðu á vandanum og skoðaðu svo tæknina",
        body: "Opnaðu [verkefnaskrána](/projects) með spurningu í huga: er þar eitthvað sem hjálpar við verk sem þú vinnur, tengist áhugamáli þínu eða færni sem þú vilt læra? Skoðaðu flokka og lýsingar áður en þú takmarkar leitina við ákveðið forritunarmál.\n\nSem dæmi lýsir [verkefnasíða Fundið](/projects/fundid-is) kortaþjónustu fyrir týnda og fundna muni á Íslandi. Hún sýnir hvernig hversdagslegur vandi getur leitt þig að verkefni. Skoðaðu verkefnasíðuna og vefinn sem hún tengir á til að kanna núverandi virkni. Lýsing í verkefnaskrá er upphafspunktur til að kynna sér verkið, ekki óháð úttekt á því.",
      },
      {
        title: "Hvað ættir þú að kanna áður en þú prófar verkefni?",
        body: "Lestu hvernig höfundurinn lýsir stöðu verkefnisins og leitaðu að tengli á vef eða prufuútgáfu. Frumgerð getur hentað vel til að gefa ábendingar þótt hún sé ekki tilbúin til daglegrar notkunar. Þjónusta sem er komin í notkun getur líka haft þekktar takmarkanir.\n\n- **Tilgangur:** getur þú útskýrt fyrir hverja verkefnið er?\n- **Aðgangur:** getur þú prófað það eða sýnir síðan verk í vinnslu?\n- **Virkni:** segja færslur eða umræður til um hvað er að gerast núna?\n- **Óskir um aðstoð:** hefur höfundurinn lýst hvers konar ábendingar eða framlög kæmu að gagni?\n\nFáar nýlegar færslur sanna ekki að verkefni hafi verið lagt niður. Ef staðan skiptir þig máli skaltu spyrja höfundinn í stað þess að álykta út frá dagsetningu einni saman.",
      },
      {
        title: "Prófaðu eitt verk og skráðu hvað gerist",
        body: "Veldu lítið verk sem samræmist tilgangi verkefnisins. Skráðu hvar þú byrjaðir, hvað þú gerðir og hvort niðurstaðan varð eins og þú bjóst við. Notaðu dæmigögn þegar þú kynnist nýju verkfæri.\n\nEf verkið tekst ekki skaltu skrá skjáinn, tækið og skrefin sem þarf til að endurtaka vandann. Ef það tekst skaltu segja hvað hjálpaði þér. Hvort tveggja gefur meira en almenn einkunn. Í [leiðarvísinum um gagnlega endurgjöf](/guides/share-a-side-project/get-useful-feedback) er snið sem þú getur notað til að skrá niðurstöður.",
      },
      {
        title: "Fylgstu með eða bentu á verkefni sem vantar",
        body: "Fylgdu verkefnum sem þú vilt skoða aftur og notaðu umræðusvæði þeirra til að spyrja afmarkaðra spurninga. Ef þú vilt hjálpa skaltu fyrst leita að kóðasafni eða leiðbeiningum frá höfundi. Skráning á Naglasúpunni þýðir ekki að hugbúnaðurinn sé opinn.\n\nEf þú þekkir verkefni annarra sem á heima í samfélaginu býður [skráningarsíðan](/create) upp á valkostinn **Tipoff**. Skráðu þig inn, gefðu upp vefslóð og tilgreindu höfund rétt. Ábendingin á að hjálpa fólki að finna upprunalega verkið. Hún gerir þig ekki að eiganda og merkir ekki að höfundurinn sé að leita að samstarfsfólki.",
      },
    ],
  },
  "iceland-developer-community/get-involved": {
    title: "Hvernig tekur þú þátt í samfélagi hugbúnaðarfólks á Íslandi?",
    description: "Taktu þátt í gegnum verkefni: kynntu þig, gefðu gagnlegar ábendingar eða bjóddu fram afmarkaða aðstoð án þess að vera með fullbúið forrit.",
    summary: "Gagnleg kynning tengir áhuga þinn við verk annarra. Veldu verkefni, útskýrðu hvað þú prófaðir eða tókst eftir og stingdu upp á litlu næsta skrefi. Þú getur lagt þitt af mörkum með forritun, hönnun, skrifum, prófunum eða sem áhugasamur notandi.",
    action: { href: "/projects", label: "Kynnast fólki í gegnum verkefnin" },
    sections: [
      {
        title: "Þú getur tekið þátt áður en þú hefur eigið verkefni",
        body: "Byrjaðu sem notandi ef þú veist ekki hvað þú getur boðið fram. Prófaðu ferli og lýstu því sem var skýrt eða ruglingslegt. Ef þú hefur gaman af skrifum skaltu kanna hvort lýsingin eða uppsetningarleiðbeiningarnar séu skiljanlegar fyrir nýliða. Ef þú þekkir viðfangsefnið skaltu lýsa raunverulegum aðstæðum sem höfundurinn hefur kannski ekki hugsað um.\n\nÞetta eru hugmyndir að aðstoð, ekki opin boð frá öllum höfundum. Lestu fyrst hvað óskað er eftir í verkefninu. Afmarkað og viðeigandi boð er auðveldara að taka afstöðu til en almennt loforð um að hjálpa við hvað sem er.",
      },
      {
        title: "Kynning sem þú getur lagað að þér",
        body: "Notaðu þetta dæmi sem grunn og settu inn atriði sem eiga við það sem þú gerðir:\n\n> Hæ, ég er að læra framendaforritun og prófaði verkefnið þitt í símanum. Ég komst í gegnum fyrsta skrefið en sá ekki hvort breytingarnar hefðu vistast. Myndi stutt skjáupptaka af ferlinu hjálpa? Ég gæti tekið hana um helgina.\n\nSkilaboðin gefa samhengi, nefna athugun, spyrja spurningar og setja hóflegar væntingar. Höfundurinn getur þegið boðið, bent á annað eða afþakkað án þess að þurfa að finna verkefni fyrir þig.\n\nÁ [samskiptasíðunni](/about/contact) eru leiðir til að komast í samband við samfélagið. Hafðu spurningar um tiltekið verkefni á umræðusvæði þess þegar það á við, svo aðrir geti lært af svarinu.",
      },
      {
        title: "Komið ykkur saman um lítið fyrsta skref",
        body: "Staðfestu hvað þú ætlar að skila og hvernig höfundurinn vill fá það áður en þú byrjar. Skjámynd með athugasemdum, lagfæring á leiðbeiningum eða endurtakanleg villulýsing getur verið fullbúið framlag. Þú þarft ekki að skuldbinda þig strax til langvarandi samstarfs.\n\nEf verkið stækkar skaltu staldra við og semja um næsta hluta. Segðu skýrt hvenær þú hefur tíma og láttu vita ef þú þarft að hætta. [Gátlistinn fyrir fyrsta framlag](/guides/contribute-to-projects/first-contribution) lýsir ferlinu nánar.",
      },
      {
        title: "Komdu eigin verkum inn í samtalið",
        body: "Þegar þú hefur eitthvað að sýna skaltu útskýra vandann og núverandi stöðu. Afmörkuð spurning eins og „Er ljóst á þessum skjá hvað á að gera næst?“ er auðveldari viðureignar en „Einhverjar hugmyndir?“\n\n[Leiðarvísirinn um að deila hliðarverkefni](/guides/share-a-side-project) fjallar um að undirbúa síðu, senda hana í yfirferð og fylgja eftir. Ef samfélagskeppni vekur áhuga þinn skaltu lesa upplýsingar um hana og skrá verkefnið sérstaklega. Að vera í verkefnaskránni og að taka þátt í keppni eru tvær ólíkar ákvarðanir.",
      },
    ],
  },
  "share-a-side-project": {
    title: "Hvernig deilir þú hliðarverkefni og færð gagnlega endurgjöf?",
    description: "Undirbúðu skýra verkefnasíðu, deildu hliðarverkefni með íslensku hugbúnaðarsamfélagi og nýttu ábendingar til að velja næsta skref.",
    summary: "Lýstu vandanum, núverandi stöðu verkefnisins og einni spurningu sem þú vilt fá hjálp við að svara. Á Naglasúpunni byrjar þú á drögum, undirbýrð verkefnasíðuna og sendir hana í yfirferð. Skráning í keppni er sérstök aðgerð.",
    action: { href: "/create", label: "Stofna drög að verkefni" },
    sections: [
      {
        title: "Hverju getur þú deilt áður en verkefni er fullbúið?",
        body: "Deildu útgáfu sem gefur öðrum eitthvað áþreifanlegt til að skilja eða prófa. Það gæti verið afmörkuð prufuútgáfa eða síða með skjámyndum og skýringu á því sem virkar. Segðu hvað vantar svo fólk rugli ekki frumgerð saman við fullbúna þjónustu.\n\nÁkveddu hvað þú vilt læra áður en þú skrifar síðuna. Er lýsingin á vandanum óskýr? Getur fólk lokið aðalverkinu? Leysir niðurstaðan vandann sem þú ætlaðir að leysa? Ein þessara spurninga dugar fyrir fyrstu beiðni um ábendingar.\n\nNotaðu [gátlistann fyrir verkefnasíðu](/guides/share-a-side-project/project-page-checklist) til að breyta þessum ákvörðunum í læsilega lýsingu og gagnlega kynningu.",
      },
      {
        title: "Hvernig bætir þú verkefni við á Naglasúpunni?",
        body: "Skráðu þig inn og opnaðu [Create a project](/create). Gefðu upp vefslóð verkefnisins og veldu **Mine** ef þú bjóst það til. Við það verða til drög sem þú getur unnið í áður en þú sendir verkefnið til birtingar. Ef þú ert að benda á verk annarra skaltu velja **Tipoff** og tilgreina höfund skýrt.\n\nFylltu út verkefnaupplýsingarnar í ritlinum og fylgdu ábendingum hans um það sem vantar fyrir birtingu. Verkefni sem sent er til birtingar bíður samþykkis. Ekki gera ráð fyrir að það sjáist í opinberu skránni fyrr en þeirri yfirferð er lokið. Þú kemst aftur að verkefninu í [My Projects](/my-projects).\n\nEf þú vilt taka þátt í keppni skaltu kynna þér upplýsingar um hana og skrá verkefnið sérstaklega. Verkefni fer ekki sjálfkrafa í keppni við skráningu, og samþykki í verkefnaskrá tryggir ekki tiltekinn árangur í keppni.",
      },
      {
        title: "Spyrðu spurningar sem getur haft áhrif á ákvörðun",
        body: "„Hvað finnst þér?“ lætur þann sem svarar velja verkefnið. Lýstu frekar stuttum aðstæðum og biddu um athuganir: „Prófaðu að finna hlut nálægt þér. Hvar bjóstu við að geta síað eftir staðsetningu?“\n\nBiddu um viðráðanlegt framlag og segðu hvar þú vilt fá svör. Fáðu leyfi áður en þú birtir einkasvar sem umsögn eða dæmi. Í [leiðarvísinum um gagnlega endurgjöf](/guides/share-a-side-project/get-useful-feedback) er snið fyrir beiðni og leið til að flokka svörin.",
      },
      {
        title: "Deildu því sem þú lærðir",
        body: "Þegar svör berast skaltu flokka athuganir eftir því sem fólk var að reyna að gera. Veldu eina breytingu, útskýrðu ástæðuna og gefðu fólki leið til að prófa nýju útgáfuna. Ef þú ákveður að fylgja ekki tillögu er stutt skýring líka gagnleg eftirfylgni.\n\nGreinar um verkefnið geta sagt frá breytingu, tilraun eða lærdómi. Hafðu færsluna afmarkaða: hvað var erfitt, hvað breyttist og hvað er enn óleyst? Þannig fá nýir gestir samhengi sem skjámynd ein veitir ekki. Ef ábendingar leiða í ljós verk sem þú þarft aðstoð við skaltu nota [leiðarvísinn um að finna samstarfsfólk](/guides/contribute-to-projects/find-collaborators) til að móta skýra beiðni.",
      },
    ],
  },
  "share-a-side-project/project-page-checklist": {
    title: "Gátlisti og sniðmát fyrir lýsingu á hliðarverkefni",
    description: "Skrifaðu verkefnalýsingu sem útskýrir vandann, sýnir hvað virkar, getur þeirra sem lögðu hönd á plóg og óskar eftir afmarkaðri endurgjöf.",
    summary: "Gagnleg verkefnasíða svarar fimm spurningum: fyrir hverja er verkefnið, hvað hjálpar það þeim að gera, hvað virkar í dag, hvernig er hægt að prófa það og hvaða ábendingar myndu hjálpa? Gerðu svörin sýnileg áður en þú bætir við langri tæknisögu.",
    action: { href: "/create", label: "Stofna verkefnisdrög" },
    sections: [
      {
        title: "Byrjaðu á því sem verkefnið hjálpar fólki að gera",
        body: "Skrifaðu setningu sem tengir saman manneskju, verk og niðurstöðu. Tilbúið dæmi: „Sameiginlegt æfingadagatal sem hjálpar litlum hljómsveitum að finna tíma sem hentar öllum.“ Það segir gesti meira en „Framsækin heildarlausn fyrir tímaskipulag.“\n\nLýstu síðan stöðunni á einföldu máli: smellanleg frumgerð, fyrsta útgáfa sem virkar eða þjónusta sem hægt er að nota í dag. Útskýrðu mikilvægar takmarkanir við hlið þeirrar virkni sem þær hafa áhrif á. Geymdu tæknilegu smáatriðin fyrir lesendur sem vilja skilja hvernig verkefnið er byggt eða leggja því lið.",
      },
      {
        title: "Notaðu þetta snið fyrir verkefnalýsinguna",
        body: "Skiptu hverri spurningu út fyrir staðreyndir um verkefnið þitt. Þetta er gátlisti fyrir efnið, ekki upptalning á skyldureitum í ritlinum.\n\n- **Vandinn:** hver lendir í honum og hvað er erfitt í dag?\n- **Verkefnið:** hvað getur fólk gert með því?\n- **Núverandi staða:** hvað virkar og hvað er enn á tilraunastigi eða vantar?\n- **Prófun:** hvar á fólk að byrja og hvaða verk á það að prófa?\n- **Óskir um ábendingar:** hvaða einu spurningu þarftu helst að fá svarað næst?\n- **Framlög:** hver bjó verkefnið til og hvernig á að geta þeirra sem lögðu hönd á plóg?\n- **Tæknilegt samhengi:** hvaða tækni eða tenglar á kóðasöfn hjálpa mögulegum þátttakanda?\n\nEkki fylla í eyður með áætlaðri notkun, ósönnuðum árangri eða eiginleikum sem þú hefur ekki smíðað. Skýrt orðaðar takmarkanir hjálpa gestum að gefa viðeigandi ábendingar.",
      },
      {
        title: "Veldu skjámyndir sem útskýra upplifunina",
        body: "Sýndu aðalverkið á raunverulegum skjá. Merki gefur verkefninu auðkenni, en skjámynd getur útskýrt hvað notandinn gerir. Hafðu nægt samhengi til að skjárinn sé skiljanlegur og fjarlægðu einkaupplýsingar úr myndinni.\n\nSkoðaðu síðuna á mjóum skjá. Lestu lýsinguna án þess að gera ráð fyrir að gesturinn þekki hugtökin þín. Opnaðu prufutengilinn án innskráningar og kannaðu hvort hægt sé að byrja þar sem lýsingin segir til um. Ef aðgangur er takmarkaður skaltu útskýra það áður en þú biður fólk að prófa.",
      },
      {
        title: "Áður en þú sendir verkefnasíðuna inn",
        body: "Farðu yfir vefslóð, lýsingu, myndir og upplýsingar um höfunda. Fylgdu athugunum ritilsins um það sem þarf fyrir birtingu. Þessi gátlisti hjálpar til við að gera efnið skýrt, en viðmótið segir til um hvort drögin séu tilbúin til innsendingar.\n\nVerkefni sem sent er til birtingar fer í yfirferð. Bíddu eftir samþykki áður en þú segir öðrum að það sé komið í opinberu verkefnaskrána. Þegar það er sýnilegt skaltu deila opinbera tenglinum með afmarkaðri beiðni samkvæmt [sniðinu fyrir endurgjöf](/guides/share-a-side-project/get-useful-feedback). Ef keppni á við skaltu lesa upplýsingarnar og skrá verkefnið sérstaklega.",
      },
    ],
  },
  "share-a-side-project/get-useful-feedback": {
    title: "Hvernig færðu gagnlega endurgjöf á hliðarverkefni?",
    description: "Spyrðu afmarkaðrar spurningar, gefðu fólki raunhæft verk til að prófa og nýttu athuganir þess við næstu endurbætur á hliðarverkefninu.",
    summary: "Gagnleg endurgjöf byrjar á verki og ákvörðun. Segðu fólki hvað það á að prófa, spurðu hvað gerðist og útskýrðu hvað þú vilt læra. Skráðu athuganir aðskildar frá tillögum að lausnum svo þú getir ákveðið hverju á að breyta.",
    action: { href: "/my-projects", label: "Opna verkefnin þín" },
    sections: [
      {
        title: "Veldu spurninguna áður en þú biður um skoðanir",
        body: "Ólíkar spurningar kalla á ólíka þátttakendur. Manneskja sem þekkir vandann getur sagt hvort ferlið henti þörfum hennar. Nýliði í viðfangsefninu getur sýnt hvar skýringin bregst. Forritari getur hjálpað við að skoða tæknilega bilun.\n\nSkrifaðu niður ákvörðunina sem þú ætlar að taka eftir samtalið. Til dæmis: „Ætti ég að útskýra kortið áður en ég bið fólk að bæta við hlut?“ Þá getur þú beðið þátttakanda að prófa það verk í stað þess að spyrja hvort öll lausnin sé góð. Nokkur samtöl geta leitt í ljós gagnleg vandamál en segja ekki til um hversu algeng þau eru meðal allra notenda.",
      },
      {
        title: "Beiðni um endurgjöf sem þú getur endurnýtt",
        body: "Lagaðu þetta dæmi að verki sem verkefnið þitt styður:\n\n> Ég er að kanna hvort fyrstu skrefin séu skiljanleg. Gætirðu opnað prufuútgáfuna og búið til eina færslu? Segðu mér hvar þú hikaðir, hverju þú bjóst við og hvort þú komst að staðfestingarskjánum. Dæmigögnunum má eyða. Nokkrar setningar hér í umræðunni myndu hjálpa.\n\nLáttu viðeigandi tengil fylgja og nefndu það sem þarf til að fá aðgang. Forðastu að útskýra hvern smell fyrirfram ef þú vilt kanna hvort skjárinn sé skiljanlegur. Ef notandinn festist skaltu skrá hvar það gerðist áður en þú hjálpar honum áfram.",
      },
      {
        title: "Aðgreindu það sem gerðist frá hugmyndum að lausn",
        body: "Haltu einfalda skrá yfir hvert svar:\n\n- **Verk:** hvað þátttakandinn reyndi að gera.\n- **Athugun:** hvað gerðist eða hvar hann hikaði.\n- **Samhengi:** tæki, vafri, viðeigandi reynsla eða aðgangsvandi.\n- **Tillaga:** lausn sem viðkomandi stakk upp á.\n- **Næsta skref:** rannsaka, breyta, spyrja nánar eða fresta.\n\n„Fann ekki hvar á að vista“ er athugun. „Hafðu hnappinn grænan“ er tillaga að lausn. Athugunin getur verið gagnleg þótt önnur lausn passi betur við viðmótið. Við villutilkynningu skaltu bæta við stystu skrefaröðinni sem endurtekur villuna og væntri niðurstöðu.",
      },
      {
        title: "Svaraðu og prófaðu breytinguna",
        body: "Þakkaðu viðkomandi fyrir það tiltekna atriði sem hann hjálpaði þér að sjá. Útskýrðu breytinguna sem þú gerðir eða hvers vegna þú frestar henni. Bjóddu síðan viðkomandi að prófa sama verk aftur ef tími gefst. Ekki túlka jákvæð ummæli sem sönnun á notkun og ekki birta einkasvör án leyfis.\n\nÁ Naglasúpunni er gott að halda beiðninni nálægt verkefninu og nota grein þegar þú hefur ítarlegri lærdóm að deila. Lýstu til dæmis ruglingslegu aðgerðinni, breytingunni og því sem á eftir að kanna. Ef verkið kallar á færni annarra skaltu skrifa [afmarkaða samstarfsbeiðni](/guides/contribute-to-projects/find-collaborators) svo næsta beiðni verði jafn skýr.",
      },
    ],
  },
  "contribute-to-projects": {
    title: "Hvernig leggur þú hugbúnaðarverkefni lið?",
    description: "Finndu gagnlegt fyrsta framlag, komdu þér saman við höfund um umfangið og taktu þátt með forritun, leiðbeiningum, hönnun eða prófunum.",
    summary: "Byrjaðu á að skilja verkefnið og spyrja hvað myndi hjálpa. Komið ykkur saman um eitt lítið framlag, fylgdu leiðbeiningum höfundarins og skildu eftir nægt samhengi til að hægt sé að yfirfara verkið. Framlag getur falist í prófunum, skrifum, hönnun eða kóða.",
    action: { href: "/projects", label: "Skoða verkefni sem þú gætir aðstoðað" },
    sections: [
      {
        title: "Veldu verkefni sem þú getur skilið og notað",
        body: "Skoðaðu [verkefnin á Naglasúpunni](/projects) og veldu eitt sem fæst við vanda sem vekur áhuga þinn. Prófaðu aðalferlið eða lestu leiðbeiningarnar áður en þú stingur upp á breytingum. Þá tengist boð þitt raunverulegum þörfum verkefnisins.\n\nLeitaðu í tenglum höfundarins að leiðbeiningum um framlög og opnum verkum. Opinber verkefnasíða er ekki sjálfkrafa boð um að breyta kóðanum og segir ekki til um hvort opið hugbúnaðarleyfi gildi. Ef engar leiðbeiningar eru til staðar skaltu spyrja stuttrar spurningar í umræðu verkefnisins.\n\n[Gátlistinn fyrir fyrsta framlag](/guides/contribute-to-projects/first-contribution) hjálpar þér að velja verk og undirbúa gagnleg skil.",
      },
      {
        title: "Hverju getur þú lagt lið öðru en kóða?",
        body: "Gagnlegt framlag fjarlægir tiltekna hindrun fyrir fólk sem smíðar eða notar verkefnið. Það gæti verið að skrá uppsetningarskref, endurtaka villu, útskýra óljóst hugtak, prófa útlit í síma eða yfirfara íslenska þýðingu. Spyrðu hvort óskað sé eftir verkinu áður en þú byrjar á stórri endurskoðun.\n\n[Open Source Guides frá GitHub](https://opensource.guide/how-to-contribute/) lýsa ýmsum leiðum til þátttöku og hvernig má nálgast verkefni. Leiðbeiningar verkefnisins sjálfs ráða því hvar á að skila framlagi og hvernig yfirferð fer fram. Ráðin hér eiga einnig við samstarf þar sem kóðinn er ekki opinber.",
      },
      {
        title: "Semjið um verkið og yfirferðina",
        body: "Áður en þú byrjar skaltu staðfesta niðurstöðuna sem stefnt er að, hver muni yfirfara hana og hversu miklum tíma þú getur varið. „Prófa skráningarferlið á litlum skjá og senda merktar skjámyndir“ er auðveldara að meta en „Bæta notendaupplifunina“.\n\nLáttu snemma vita ef aðgangur eða tæknileg ákvörðun hindrar þig. Lítið framlag þarf skýran endapunkt: skýrslu skilað, texta yfirfarinn eða breytingu prófaða. Að klára eitt lítið verk gefur báðum aðilum grunn til að ákveða hvort þeir vilji halda áfram.\n\nEf þú ert höfundurinn sem óskar eftir hjálp skaltu nota [sniðið fyrir samstarfsbeiðni](/guides/contribute-to-projects/find-collaborators) til að gera væntingarnar sýnilegar.",
      },
      {
        title: "Gerðu verkið auðvelt í yfirferð",
        body: "Lýstu því sem breyttist, hvers vegna og hvernig þú kannaðir það. Láttu skjámyndir fylgja sjónrænum atriðum og skref til að endurtaka villur. Haltu ótengdum hugmyndum til hliðar svo hægt sé að meta eitt verk í einu.\n\nSegðu opinskátt frá því sem er óklárað og ákvörðunum sem þú þarft hjálp við. Framlag er boð um verk til yfirferðar; höfundurinn getur óskað eftir breytingum eða valið aðra leið. Þegar verkið er samþykkt skaltu semja um hvernig framlagsins verði getið og skrá það sem næsti þátttakandi þarf að vita. Slíkar leiðbeiningar auðvelda næsta manni fyrsta skrefið.",
      },
    ],
  },
  "contribute-to-projects/first-contribution": {
    title: "Gátlisti fyrir fyrsta framlag þitt til hugbúnaðarverkefnis",
    description: "Veldu lítið framlag, lestu leiðbeiningar verkefnisins, semdu um umfangið og skilaðu verki sem umsjónaraðili getur yfirfarið.",
    summary: "Veldu fyrsta framlag sem þú getur útskýrt í einni setningu og lokið með skýrum skilum. Lestu leiðbeiningar verkefnisins, staðfestu að verkið sé vel þegið, gerðu minnstu gagnlegu breytinguna og lýstu því hvernig þú kannaðir hana.",
    action: { href: "/projects", label: "Velja verkefni" },
    sections: [
      {
        title: "Kynntu þér verkefnið áður en þú velur verk",
        body: "Lestu lýsinguna og prófaðu þann hluta sem vekur áhuga þinn. Ef tengt er á kóðasafn skaltu leita að README-skrá, leiðbeiningum fyrir þátttakendur, opnum verkum og samskiptareglum. Athugaðu hvort einhver sé þegar að vinna að því sem þú ætlar að leggja til.\n\nTil dæmis er tengill á [kóðasafn Naglasúpunnar](https://github.com/alexcouper/nglspn) í síðufæti þessa vefs. Leiðbeiningarnar þar eru upphafspunktur fyrir vinnu við þennan vettvang. Ekki gera ráð fyrir að önnur verkefni noti sömu tækni eða verkferla. Þótt verkefni hafi ekkert opinbert kóðasafn getur þú mögulega hjálpað með villulýsingu eða yfirferð á viðmóti.",
      },
      {
        title: "Skilgreindu eina niðurstöðu og spurðu hvort hún hjálpi",
        body: "Góð fyrstu verk hafa sýnilegan endi: endurtaka eina villu, skýra eitt uppsetningarskref eða prófa einn skjá í þröngum glugga. Forðastu víðtæka endurskrifun áður en þú þekkir forsendur verkefnisins.\n\nSendu stutta tillögu: „Í uppsetningarleiðbeiningunum kemur ekki fram hvaða skipun ræsir framendann. Ég get prófað núverandi skref og lagt til litla textabreytingu. Myndi það hjálpa og er einhver þegar að vinna í þessu?“\n\nUmsjónaraðilinn gæti stungið upp á öðru verki. Skýrt umfang frá upphafi sparar báðum aðilum yfirferð. Ef ekkert svar berst skaltu velja annað skráð verk eða verkefni í stað þess að gera ráð fyrir samþykki fyrir stórri breytingu.",
      },
      {
        title: "Skilaðu einhverju sem hægt er að yfirfara",
        body: "Fylgdu skilaleið verkefnisins. Fyrir kóðabreytingu skaltu nota skjalfestar skipanir fyrir þróun og prófanir. Í villulýsingu skaltu nefna umhverfið, skref til að endurtaka vandann, vænta niðurstöðu og raunverulega niðurstöðu. Fyrir leiðbeiningar skaltu prófa breyttu skrefin frá upphafspunkti lesandans.\n\nNotaðu þennan gátlista við skil:\n\n- Lýstu vandanum og tengdu á samþykkta verkið ef það er skráð.\n- Útskýrðu breytinguna eða athugunina í fáeinum setningum.\n- Lýstu þeim prófunum sem þú framkvæmdir í raun.\n- Nefndu það sem er ólokið eða óvíst.\n- Spyrðu afmarkaðrar spurningar ef þú þarft ákvörðun frá yfirlesara.\n\nHaltu einkaupplýsingum utan skjámynda og annála sem þú birtir opinberlega.",
      },
      {
        title: "Svaraðu yfirferðinni og veldu næsta skref",
        body: "Líttu á athugasemdir við yfirferð sem upplýsingar um þarfir verkefnisins. Biddu um skýringu ef breytingabeiðni er óljós og segðu frá því ef hún krefst meiri tíma en þú getur boðið. Umsjónaraðilinn ákveður hvort verkið sé samþykkt; innsending tryggir ekki að það verði tekið inn.\n\nÞegar verkinu er lokið skaltu skrá leiðbeiningar sem vantaði og gætu hjálpað næsta nýliða. Þú getur látið þar við sitja eða samið um annað lítið verk. Sjá nánara samhengi í [leiðarvísi GitHub um framlög til opins hugbúnaðar](https://opensource.guide/how-to-contribute/). Ef þú vilt lengra samstarf skaltu gera ábyrgðina skýra með [samstarfslýsingu](/guides/contribute-to-projects/find-collaborators).",
      },
    ],
  },
  "contribute-to-projects/find-collaborators": {
    title: "Hvernig finnur þú samstarfsfólk fyrir hliðarverkefni?",
    description: "Skrifaðu skýra samstarfsbeiðni sem lýsir hliðarverkefninu, aðstoðinni sem þú þarft, tímaskuldbindingu og fyrsta verkinu.",
    summary: "Gerðu beiðnina nógu afmarkaða til að hægt sé að svara henni. Útskýrðu verkefnið, sýndu hvað er til, nefndu aðstoðina sem þú þarft og leggðu til fyrsta verk með skýrum endapunkti. Vertu skýr um tíma, væntingar um greiðslur og hvernig ákvarðanir verða teknar.",
    action: { href: "/my-projects", label: "Bæta upplýsingum við verkefnið þitt" },
    sections: [
      {
        title: "Sýndu hvað er til áður en þú lýsir framtíðarsýninni",
        body: "Samstarfsaðili þarf að skilja bæði tilganginn og upphafspunktinn. Tengdu á verkefnasíðu, prufuútgáfu, skjámyndir eða kóðasafn sem viðkomandi getur skoðað. Lýstu vandanum á venjulegu máli og nefndu hvað stendur í vegi fyrir framvindu.\n\n„Hjálpaðu okkur að móta framtíð viðburða í nærumhverfinu“ er erfitt að bregðast við. „Viðburðalistinn virkar, en okkur vantar hjálp við að kanna hvort fólk finni viðburði nálægt sér í símanum“ gefur mögulegum þátttakanda eitthvað til að meta. Undirbúðu [verkefnasíðuna](/guides/share-a-side-project/project-page-checklist) áður en þú vísar fólki þangað.",
      },
      {
        title: "Snið fyrir samstarfsbeiðni",
        body: "Skrifaðu eftirfarandi niður áður en þú biður einhvern að taka þátt:\n\n- **Tilgangur:** fólkið og vandinn sem verkefnið þjónar.\n- **Núverandi staða:** hvað virkar og hvar er hægt að sjá það?\n- **Aðstoð:** tiltekið verk og færnin sem það kallar á.\n- **Fyrsta niðurstaða:** hvernig lítur fullbúið fyrsta framlag út?\n- **Skuldbinding:** tíminn sem þið getið hvort um sig boðið og hugsanleg tímamörk.\n- **Fyrirkomulag:** hvort framlagið er sjálfboðavinna eða greitt verk; láttu það ekki liggja á milli hluta.\n- **Samvinna:** hver yfirfer verkið, hvar samskipti fara fram og hvernig framlagsins verður getið.\n\nTil dæmis: „Ég er með frumgerð af viðburðalista sem virkar. Ég leita að einhverjum til að yfirfara síurnar í síma og senda merktar skjámyndir. Þetta er afmörkuð yfirferð í sjálfboðavinnu; ég get svarað spurningum um helgina og mun geta framlagsins með þínu leyfi.“",
      },
      {
        title: "Deildu beiðninni þar sem samhengi verkefnisins sést",
        body: "Settu beiðnina við verkefnalýsinguna eða í færslu og tengdu á hana þegar þú kynnir verkið í samfélaginu. Á [samskiptasíðu Naglasúpunnar](/about/contact) eru leiðir að umræðuvettvangi samfélagsins. Fylgdu venjum og reglum þess svæðis sem þú notar.\n\nBjóddu upp á spurningar og gerðu auðvelt að afþakka. Forðastu að senda sömu almennu beiðnina á alla höfunda í skránni. Ef einhver hefur unnið að tengdu verki skaltu nefna tenginguna og spyrja hvort viðkomandi vilji ræða verkefnið. Skráning í verkefnaskrá þýðir ekki að fólk sé laust til samstarfs.",
      },
      {
        title: "Prófið eitt verk áður en samstarfið stækkar",
        body: "Komið ykkur saman um afurðina og yfirferðina áður en vinna hefst. Ræðið eftir fyrsta verkið hvað gekk vel, hvað var óljóst og hvort þið viljið bæði halda áfram. Uppfærið lýsinguna ef umfangið breytist.\n\nHafið aðgang og ábyrgð í samræmi við verkið. Skráið mikilvægar ákvarðanir þar sem báðir aðilar finna þær og semjið um hvernig vinnu verður skilað ef annar þarf að hætta. [Gátlistinn fyrir fyrsta framlag](/guides/contribute-to-projects/first-contribution) getur hjálpað nýjum samstarfsaðila að undirbúa skýr skil á meðan þú gerir ráð fyrir tíma til að yfirfara þau.",
      },
    ],
  },
};

export const icelandicGuides: Guide[] = guides.map((guide) => {
  const translation = translations[guide.slug];
  if (!translation || translation.sections.length !== guide.sections.length) {
    throw new Error(`Missing or incomplete Icelandic guide: ${guide.slug}`);
  }
  return {
    ...guide,
    ...translation,
    sections: guide.sections.map((section, index) => ({
      id: section.id,
      ...translation.sections[index],
    })),
  };
});
