/// Build-time configuration injected via --dart-define-from-file.
///
/// Values are compiled into the binary — they are NOT bundled as a readable
/// asset file and cannot be extracted from the APK with standard tools.
///
/// Build commands:
///   Debug   : flutter run  --dart-define-from-file=dart_defines.json
///   Release : flutter build apk --dart-define-from-file=dart_defines.json
///
/// dart_defines.json (never commit this file — add to .gitignore):
/// {
///   "FACE_RECOGNITION_API_URL": "https://your-production-domain.com/api/attendance/clock-in-face",
///   "FACE_RECOGNITION_WEB_URL": "https://your-production-domain.com/api/attendance/clock-in-face"
/// }
class AppConfig {
  AppConfig._();

  /// REST endpoint used by the native camera path (Android/iOS).
  static const String apiUrl = String.fromEnvironment(
    'FACE_RECOGNITION_API_URL',
    defaultValue: 'http://10.0.2.2:8080/api/attendance/clock-in-face',
  );

  /// REST endpoint used by the web/desktop camera path.
  static const String webUrl = String.fromEnvironment(
    'FACE_RECOGNITION_WEB_URL',
    defaultValue: 'http://localhost:8080/api/attendance/clock-in-face',
  );
}
