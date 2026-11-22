import '../l10n/l10n.dart';

/// Build-time app metadata.
///
/// There is no package_info plugin in the dependency set, so the version is a
/// constant kept in sync with `pubspec.yaml` (`version: 1.0.2+1`). Release builds can
/// override it: `flutter build apk --dart-define=DSH_APP_VERSION=1.2.0+7`.
abstract final class AppInfo {
  static const version = String.fromEnvironment('DSH_APP_VERSION', defaultValue: '1.0.2+1');

  /// "1.0.0 (1)" for display.
  static String get displayVersion {
    final parts = version.split('+');
    return parts.length == 2 ? '${parts[0]} (${parts[1]})' : version;
  }

  /// The app's name as the phone shows it: launcher, Recents, notifications, system
  /// settings, the licence page. Matches `android:label` in AndroidManifest.xml.
  static const name = 'dsh边界';

  /// The in-app wordmark: the drawer's lockup, the welcome page and the brand mark's
  /// spoken label.
  static const wordmark = 'dsh边界';

  /// Required wording: the app is built on DSH but is not an official DeepSeek product.
  /// Shown on the About and licence pages.
  static String get disclaimer => appL10n.stateAppDisclaimer;

  /// The line under the brand mark (welcome page, 关于 dsh边界).
  static String get slogan => appL10n.appSlogan;

  /// Who maintains this build, and their personal profiles.
  ///
  /// This is the fork's maintainer, not the dsh-go project's original author:
  /// `ccch1mneyyy` built dsh-go, which this app derives from, and is credited
  /// as such in THIRD_PARTY_NOTICES.md. Listing them here as "the author"
  /// would both misattribute this build and imply an endorsement it does not
  /// have. They have no Bilibili or X profile here for the same reason.
  static const author = 'wuwei-123';
  static const authorBilibiliName = '';
  static const authorBilibiliUrl = '';
  static const authorXHandle = '';
  static const authorXUrl = '';
  static const authorGithubUrl = 'https://github.com/wuwei-123';

  static const deepseekPlatform = 'https://platform.deepseek.com/api_keys';
  static const remoteConsole = 'https://dsh.r2049.cn/app';

  /// DSH Remote's upstream, credited under the DSH Remote card as its GitHub
  /// handle and name.
  static const remoteProject = 'liguobao/ds-harness-remote';
  static const remoteProjectUrl = 'https://github.com/$remoteProject';
}
