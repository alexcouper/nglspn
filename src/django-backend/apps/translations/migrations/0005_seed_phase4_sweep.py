from __future__ import annotations

from django.db import migrations

# (locale, key, text)
SEEDS: list[tuple[str, str, str]] = [
    # common
    ("is", "common.loading", "Hleður..."),
    ("is", "common.tryAgain", "Reyna aftur"),
    ("is", "common.cancel", "Hætta við"),
    ("is", "common.close", "Loka"),
    ("is", "common.backToHome", "Aftur á forsíðu"),
    ("is", "common.backToLogin", "Aftur í innskráningu"),
    ("is", "common.profile", "Notandi"),
    # error
    ("is", "error.heading", "Eitthvað fór úrskeiðis"),
    # auth.login
    ("is", "auth.login.heading", "Velkomin/n aftur"),
    ("is", "auth.login.subheading", "Skráðu þig inn til að sýsla með verkefnin þín"),
    ("is", "auth.login.emailLabel", "Netfang"),
    ("is", "auth.login.emailPlaceholder", "thu@daemi.is"),
    ("is", "auth.login.passwordLabel", "Lykilorð"),
    ("is", "auth.login.submitting", "Skráir inn..."),
    ("is", "auth.login.submit", "Skrá inn"),
    ("is", "auth.login.forgotPasswordLink", "Gleymt lykilorð?"),
    ("is", "auth.login.noAccount", "Ekki með aðgang?"),
    ("is", "auth.login.createLink", "Stofnaðu einn"),
    # auth.register
    ("is", "auth.register.heading", "Stofna aðgang"),
    ("is", "auth.register.subheading", "Byrjaðu að deila verkefnunum þínum í dag"),
    ("is", "auth.register.emailLabel", "Netfang"),
    ("is", "auth.register.emailPlaceholder", "thu@daemi.is"),
    ("is", "auth.register.passwordLabel", "Lykilorð"),
    ("is", "auth.register.passwordPlaceholder", "Að minnsta kosti 8 stafir"),
    ("is", "auth.register.kennitalaLabel", "Kennitala"),
    ("is", "auth.register.kennitalaPlaceholder", "10 tölustafir"),
    (
        "is",
        "auth.register.privacyAgreement",
        "Með því að stofna aðgang samþykkir þú persónuverndarstefnu okkar.",
    ),
    ("is", "auth.register.privacyLink", "Persónuverndarstefna"),
    ("is", "auth.register.submitting", "Stofnar aðgang..."),
    ("is", "auth.register.submit", "Stofna aðgang"),
    ("is", "auth.register.haveAccount", "Þegar með aðgang?"),
    ("is", "auth.register.loginLink", "Skrá inn"),
    (
        "is",
        "auth.register.passwordTooShort",
        "Lykilorð verður að vera að minnsta kosti 8 stafir",
    ),
    (
        "is",
        "auth.register.kennitalaInvalid",
        "Kennitala verður að vera nákvæmlega 10 tölustafir",
    ),
    # auth.forgot
    ("is", "auth.forgot.heading", "Gleymt lykilorð?"),
    (
        "is",
        "auth.forgot.subheading",
        "Sláðu inn netfangið þitt til að fá endursetningarkóða",
    ),
    ("is", "auth.forgot.submitting", "Sendir..."),
    ("is", "auth.forgot.submit", "Halda áfram"),
    # auth.code
    ("is", "auth.code.heading", "Sláðu inn kóðann"),
    ("is", "auth.code.subheading", "Við sendum 6 stafa kóða á {email}"),
    ("is", "auth.code.verifying", "Staðfestir..."),
    (
        "is",
        "auth.code.attemptsRemaining",
        "{count, plural, one {# tilraun eftir} other {# tilraunir eftir}}",
    ),
    # auth.reset
    ("is", "auth.reset.heading", "Setja nýtt lykilorð"),
    ("is", "auth.reset.subheading", "Veldu nýtt lykilorð fyrir aðganginn þinn"),
    ("is", "auth.reset.passwordLabel", "Nýtt lykilorð"),
    ("is", "auth.reset.submitting", "Vistar..."),
    ("is", "auth.reset.submit", "Setja lykilorð"),
    (
        "is",
        "auth.reset.successMessage",
        "Lykilorð uppfært. Vinsamlegast skráðu þig inn.",
    ),
    # onboarding.completeProfile
    ("is", "onboarding.completeProfile.heading", "Kláraðu prófílinn þinn"),
    (
        "is",
        "onboarding.completeProfile.subheading",
        "Bættu við nafninu þínu svo aðrir viti hver þú ert",
    ),
    ("is", "onboarding.completeProfile.firstNameLabel", "Fornafn"),
    ("is", "onboarding.completeProfile.firstNamePlaceholder", "Fornafnið þitt"),
    ("is", "onboarding.completeProfile.lastNameLabel", "Eftirnafn"),
    ("is", "onboarding.completeProfile.lastNamePlaceholder", "Eftirnafnið þitt"),
    ("is", "onboarding.completeProfile.submitting", "Vistar..."),
    ("is", "onboarding.completeProfile.submit", "Halda áfram"),
    # onboarding.verifyEmail
    ("is", "onboarding.verifyEmail.heading", "Staðfestu netfangið þitt"),
    (
        "is",
        "onboarding.verifyEmail.subheading",
        "Við sendum 6 stafa kóða á {email}",
    ),
    ("is", "onboarding.verifyEmail.codeSentMessage", "Kóði sendur!"),
    ("is", "onboarding.verifyEmail.verifying", "Staðfestir..."),
    ("is", "onboarding.verifyEmail.noCode", "Fékkstu ekki kóðann?"),
    ("is", "onboarding.verifyEmail.resendCooldown", "Senda aftur eftir {count}s"),
    ("is", "onboarding.verifyEmail.resend", "Senda aftur"),
    # home
    ("is", "home.submitProject", "Senda inn verkefni"),
    # projects
    ("is", "projects.submitButton", "Senda inn verkefni"),
    ("is", "projects.discoverTab", "Uppgötva"),
    ("is", "projects.untitledProject", "Verkefni án titils"),
    ("is", "projects.backToMyProjects", "Til baka í mín verkefni"),
    ("is", "projects.notFound", "Verkefni fannst ekki"),
    ("is", "projects.publishButton", "Birta"),
    ("is", "projects.deleteButton", "Eyða"),
    ("is", "projects.winnersSection.heading", "Sigurvegarar keppna"),
    ("is", "projects.newArrivals.heading", "Nýjustu verkefnin"),
    ("is", "projects.mostDiscussed.heading", "Mest rætt"),
    ("is", "projects.category.seeAll", "Sjá allt"),
    ("is", "projects.status.pending", "Í bið"),
    ("is", "projects.status.approved", "Samþykkt"),
    ("is", "projects.status.rejected", "Hafnað"),
    (
        "is",
        "projects.error.loadProjectsMessage",
        "Við gátum ekki sótt verkefnin. Þetta gæti verið tímabundið.",
    ),
    (
        "is",
        "projects.error.loadProjectMessage",
        "Við gátum ekki sótt þetta verkefni. Þetta gæti verið tímabundið.",
    ),
    # projects.deleteDialog
    ("is", "projects.deleteDialog.heading", "Eyða verkefni"),
    (
        "is",
        "projects.deleteDialog.confirmation",
        'Ertu viss um að þú viljir eyða "{title}"? Þessari aðgerð verður ekki snúið við.',
    ),
    ("is", "projects.deleteDialog.instruction", "Skrifaðu eyða til að staðfesta:"),
    ("is", "projects.deleteDialog.confirmText", "eyða"),
    ("is", "projects.deleteDialog.placeholder", "Skrifaðu 'eyða' til að staðfesta"),
    ("is", "projects.deleteDialog.deleting", "Eyðir..."),
    ("is", "projects.deleteDialog.deleteButton", "Eyða verkefni"),
    # projects.publishDialog
    ("is", "projects.publishDialog.heading", "Ekki alveg tilbúið til birtingar"),
    (
        "is",
        "projects.publishDialog.message",
        "Áður en þú birtir, vinsamlegast bættu við:",
    ),
    ("is", "projects.publishDialog.fieldTitle", "Titli"),
    ("is", "projects.publishDialog.fieldDescription", "Lýsingu"),
    ("is", "projects.publishDialog.fieldMainImage", "Aðalmynd"),
    # myProjects
    ("is", "myProjects.heading", "Mín verkefni"),
    ("is", "myProjects.subheading", "Sýsla með innsendingar þínar"),
    ("is", "myProjects.empty", "Þú hefur ekki sent inn nein verkefni enn."),
    ("is", "myProjects.submitFirst", "Sendu inn fyrsta verkefnið þitt"),
    ("is", "myProjects.submitNew", "Senda inn nýtt verkefni"),
    # myReviews
    ("is", "myReviews.heading", "Mínar umsagnir"),
    ("is", "myReviews.subheading", "Raða verkefnum fyrir keppnir"),
    # reviews.finishDialog
    ("is", "reviews.finishDialog.heading", "Ljúka umsögn?"),
    (
        "is",
        "reviews.finishDialog.confirmation",
        "Þetta læsir röðuninni þinni. Þú getur ekki gert frekari breytingar.",
    ),
    ("is", "reviews.finishDialog.finishButton", "Ljúka umsögn"),
    ("is", "reviews.finishDialog.finishing", "Lýkur..."),
    # submit
    ("is", "submit.heading", "Byrja nýtt verkefni"),
    (
        "is",
        "submit.subheading",
        "Slepptu inn slóð — þú bætir við restinni áður en þú birtir.",
    ),
    ("is", "submit.urlLabel", "Slóð verkefnis"),
    ("is", "submit.urlPlaceholder", "https://verkefnid-thitt.is"),
    ("is", "submit.submitting", "Stofnar..."),
    ("is", "submit.submitButton", "Stofna drög"),
    ("is", "submit.invalidUrl", "Vinsamlegast sláðu inn gilda slóð"),
    # competitions
    ("is", "competitions.heading", "Keppnir"),
    ("is", "competitions.subheading", "Keppnir samfélagsins og niðurstöður þeirra"),
    ("is", "competitions.pastCompetitions", "Fyrri keppnir"),
    (
        "is",
        "competitions.pendingProjects",
        "{count, plural, one {# verkefni í bið} other {# verkefni í bið}}",
    ),
    ("is", "competitions.empty", "Engar keppnir fundust."),
    (
        "is",
        "competitions.projectCount",
        "{count, plural, one {# verkefni} other {# verkefni}}",
    ),
    ("is", "competitions.status.open", "Opin"),
    ("is", "competitions.status.voting", "Atkvæðagreiðsla"),
    ("is", "competitions.status.completed", "Lokið"),
    (
        "is",
        "competitions.error.message",
        "Við gátum ekki sótt þessa keppni. Þetta gæti verið tímabundið.",
    ),
    (
        "is",
        "competitions.detail.ctaHeading",
        "Ertu með verkefni í vinnslu?",
    ),
    (
        "is",
        "competitions.detail.ctaDescription",
        "Deildu verkefninu þínu með samfélaginu og keppt í {name}",
    ),
    ("is", "competitions.detail.submitButton", "Senda inn verkefni"),
    (
        "is",
        "competitions.detail.votingMessage",
        "Atkvæðagreiðsla er í gangi. Sigurvegarinn verður tilkynntur fljótlega.",
    ),
    ("is", "competitions.detail.winnerLabel", "Sigurvegari"),
    ("is", "competitions.detail.allProjects", "Öll verkefni"),
    (
        "is",
        "competitions.detail.noProjects",
        "Engin verkefni enn — vertu fyrst/ur til að senda inn!",
    ),
    ("is", "competitions.detail.prizeLabel", "verðlaun"),
    # about
    ("is", "about.heading", "Styðjum við smiði Íslands"),
    (
        "is",
        "about.subheading",
        "Allt sem þú þarft til að deila verkum þínum og vaxa með samfélaginu.",
    ),
    ("is", "about.section1.heading", "Sýndu verkin þín"),
    (
        "is",
        "about.section1.description",
        "Vettvangur til að sýna hliðarverkefni og snemmbúnar hugmyndir fyrir íslenska tæknisamfélagið.",
    ),
    ("is", "about.section2.heading", "Fáðu endurgjöf"),
    (
        "is",
        "about.section2.description",
        "Fáðu verðmæta endurgjöf frá öðrum smiðum og keppt um verðlaun í keppnum samfélagsins.",
    ),
    ("is", "about.section3.heading", "Deildu og vaxtu"),
    (
        "is",
        "about.section3.description",
        "Deildu reynslu þinni og kunnáttu. Lærðu af öðrum. Láttu verkefnið þitt vaxa með samfélaginu.",
    ),
    ("is", "about.layout.badge", "Smiðasamfélag Íslands"),
    ("is", "about.layout.heading", "Varpaðu ljósi á\nverkin þín"),
    (
        "is",
        "about.layout.description",
        "Vettvangur fyrir íslenska forritara til að sýna hliðarverkefni, fá endurgjöf frá samfélaginu og keppa um viðurkenningu.",
    ),
    ("is", "about.layout.whatTab", "Hvað"),
    ("is", "about.layout.whyTab", "Hvers vegna"),
    ("is", "about.layout.prizesTab", "Verðlaun"),
    ("is", "about.layout.contactTab", "Hafa samband"),
    ("is", "about.why.pocHeading", "Kostnaður við frumgerð er nánast enginn"),
    ("is", "about.why.seniorHeading", "Skortur á reyndum forriturum"),
    ("is", "about.why.geopoliticsHeading", "Heimsstjórnmál og stafrænt fullveldi"),
    ("is", "about.prizes.eligibilityHeading", "Hæfi"),
    ("is", "about.prizes.selectionHeading", "Verðlaunaveiting og val"),
    ("is", "about.prizes.cta", "Tilbúin/n að senda inn verkefnið þitt?"),
    ("is", "about.prizes.ctaButton", "Byrja"),
    ("is", "about.contact.heading", "Hafa samband"),
    ("is", "about.contact.discordLabel", "Discord"),
    ("is", "about.contact.emailLabel", "Netfang"),
    # profile
    ("is", "profile.heading", "Notandi"),
    ("is", "profile.subheading", "Sýsla með aðganginn þinn"),
    ("is", "profile.editButton", "Breyta"),
    ("is", "profile.previewButton", "Forskoða"),
    ("is", "profile.saveButton", "Vista"),
    (
        "is",
        "profile.nameRequired",
        "Þarf að minnsta kosti eitt nafn (fornafn eða eftirnafn)",
    ),
    ("is", "profile.anonymousName", "Nafnlaus"),
    ("is", "profile.firstNameLabel", "Fornafn"),
    ("is", "profile.firstNamePlaceholder", "Fornafnið þitt"),
    ("is", "profile.lastNameLabel", "Eftirnafn"),
    ("is", "profile.lastNamePlaceholder", "Eftirnafnið þitt"),
    ("is", "profile.aboutLabel", "Um þig"),
    ("is", "profile.markdownBadge", "Markdown"),
    ("is", "profile.aboutPlaceholder", "Segðu okkur frá þér..."),
    (
        "is",
        "profile.aboutHelper",
        "Þetta birtist á opinberu prófílnum þínum og er tengt frá verkefnunum þínum",
    ),
    # profile.settings
    ("is", "profile.settings.heading", "Stillingar"),
    ("is", "profile.settings.description", "Sýsla með tölvupóststillingar þínar"),
    ("is", "profile.settings.competitionResults", "Niðurstöður keppna"),
    (
        "is",
        "profile.settings.competitionResultsDescription",
        "Fá tölvupóst um niðurstöður keppna og röðun",
    ),
    ("is", "profile.settings.platformUpdates", "Uppfærslur vettvangs"),
    (
        "is",
        "profile.settings.platformUpdatesDescription",
        "Fá tölvupóst um nýja eiginleika og endurbætur",
    ),
    ("is", "profile.settings.notificationsHeading", "Tilkynningar"),
    (
        "is",
        "profile.settings.notificationsDescription",
        "Hversu oft þú færð tilkynningar um umræður",
    ),
    ("is", "profile.settings.notificationImmediate", "Í hvert skipti"),
    ("is", "profile.settings.notificationHourly", "Á klukkutíma fresti"),
    ("is", "profile.settings.notificationDaily", "Daglega"),
    ("is", "profile.settings.notificationNever", "Aldrei"),
    ("is", "profile.settings.privacyHeading", "Persónuvernd"),
    ("is", "profile.settings.privacyDescription", "Sýsla með persónuverndarstillingar"),
    ("is", "profile.settings.externalPromotions", "Ytri kynningar"),
    (
        "is",
        "profile.settings.externalPromotionsDescription",
        "Leyfa að þátttaka þín verði birt á ytri vettvöngum eins og LinkedIn",
    ),
    # users
    ("is", "users.notFound", "Notandi fannst ekki"),
    # imageUpload
    ("is", "imageUpload.dropHere", "Slepptu myndum hér"),
    ("is", "imageUpload.instruction", "Smelltu til að hlaða upp eða dragðu og slepptu"),
    ("is", "imageUpload.formats", "PNG, JPG, WebP, GIF allt að 10MB"),
    (
        "is",
        "imageUpload.aspectRatio",
        "Aðalmynd er best í 16:9 hlutfalli (t.d. 1920×1080 eða 1280×720)",
    ),
    ("is", "imageUpload.slotsRemaining", "{remaining} af {maxFiles} plássum eftir"),
    ("is", "imageUpload.maxReached", "Hámark mynda náð"),
    # discussions
    ("is", "discussions.newDialog.title", "Hefja umræðu"),
    ("is", "discussions.newDialog.submitLabel", "Birta"),
    ("is", "discussions.newDialog.placeholder", "Hvað er á döfinni?"),
    (
        "is",
        "discussions.newDialog.error",
        "Mistókst að birta umræðu. Vinsamlegast reyndu aftur.",
    ),
    ("is", "discussions.newDialog.submitting", "Vistar..."),
]


def seed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for locale, key, text in SEEDS:
        Translation.objects.update_or_create(
            locale=locale,
            key=key,
            defaults={
                "text": text,
                "source_hash": "",
                "is_machine_translated": False,
                "retired": False,
            },
        )


def unseed(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    Translation.objects.filter(
        locale="is",
        key__in=[k for _, k, _ in SEEDS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("translations", "0004_seed_phase4_edit_ui"),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
