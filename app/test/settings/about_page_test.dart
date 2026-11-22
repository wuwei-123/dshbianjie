// 关于: the installed version, the update controls, and the brand mark with the
// slogan and the unofficial-app disclaimer. Nothing else.
//
// This build ships no star prompt, no maintainer profiles and no licence row,
// so the tests below assert both what the page shows and that those three are
// gone - a row reappearing would be a regression, not a nicety.

import 'package:dshbianjie_app/l10n/l10n.dart';
import 'package:dshbianjie_app/state/update_state.dart';
import 'package:dshbianjie_app/ui/settings/about_page.dart';
import 'package:dshbianjie_app/ui/theme/app_theme.dart' show buildDarkTheme, buildLightTheme;
import 'package:dshbianjie_app/update/version.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/test_fonts.dart';

class _FixedUpdate extends AppUpdateController {
  @override
  AppUpdateState build() => const AppUpdateState(current: AppVersion(1, 0, 2, build: 42));
}

/// The disclaimer exactly as the app ships it, in [english] or Chinese.
String _disclaimer(bool english) =>
    lookupL10n(english ? AppLocale.en : AppLocale.zhCN).stateAppDisclaimer;

void main() {
  tearDown(() => AppLocale.use(AppLocale.zhCN));

  Future<void> pump(
    WidgetTester tester, {
    Locale locale = AppLocale.zhCN,
    Brightness brightness = Brightness.light,
    double scale = 1,
  }) async {
    AppLocale.use(locale);
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(360, 800);
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [appUpdateProvider.overrideWith(_FixedUpdate.new)],
        child: MaterialApp(
          theme: withTestFonts(buildLightTheme()),
          darkTheme: withTestFonts(buildDarkTheme()),
          themeMode: brightness == Brightness.dark ? ThemeMode.dark : ThemeMode.light,
          locale: locale,
          supportedLocales: AppLocale.supported,
          localizationsDelegates: L10n.localizationsDelegates,
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(scale)),
            child: child!,
          ),
          home: const AboutPage(),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  for (final locale in AppLocale.supported) {
    for (final brightness in Brightness.values) {
      testWidgets('version and disclaimer fit 360dp at 1.3x in $locale $brightness', (tester) async {
        await pump(tester, locale: locale, brightness: brightness, scale: 1.3);
        final english = locale == AppLocale.en;

        expect(find.text('1.0.2 (42)'), findsOneWidget);
        // 检查更新 / 自动检查更新 are the only rows besides the version.
        expect(find.text(lookupL10n(locale).updateCheck), findsOneWidget);

        // The wording comes from the shipped strings, not a copy of them: this
        // build's disclaimer names the fork, and a hard-coded copy here would
        // silently stop testing the row it is looking for.
        final disclaimer = find.text(_disclaimer(english));
        await tester.ensureVisible(disclaimer);
        await tester.pumpAndSettle();
        expect(disclaimer.hitTestable(), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets('no star prompt, no profiles, no licence row', (tester) async {
    await pump(tester);
    final l10n = lookupL10n(AppLocale.zhCN);

    expect(find.byKey(const ValueKey('settings-star')), findsNothing);
    expect(find.text(l10n.starSettingsTitle), findsNothing);

    expect(find.text(l10n.hubAboutAuthor), findsNothing);
    expect(find.byKey(const ValueKey('about-author-github')), findsNothing);
    expect(find.byKey(const ValueKey('about-author-bilibili')), findsNothing);
    expect(find.byKey(const ValueKey('about-author-x')), findsNothing);


    expect(find.text(l10n.hubSettingsLicenses), findsNothing);
  });

  testWidgets('nothing on the page opens a browser', (tester) async {
    // 关于 has no external links any more, so a tap anywhere must leave the app
    // where it is: the update rows navigate, and that is all that is left.
    await pump(tester);
    await tester.tap(find.text('1.0.2 (42)'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.byType(AboutPage), findsOneWidget);
  });
}
