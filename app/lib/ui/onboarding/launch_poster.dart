// The first-run poster backdrop: the brand artwork behind the welcome page.
//
// Why it exists: the Android window background (`launch_background.xml`) only
// shows for a moment — Android 12+ draws the system splash on top, and Flutter's
// first frame replaces the window right after. So the poster has to be painted
// by Flutter itself to be actually seen.
//
// It uses the same AppBackdrop.picture seam the custom wallpaper uses, so the
// page keeps its normal gradient behaviour when the image cannot be decoded.

import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// The poster, decoded once per process and kept for the app's life.
///
/// Decoded at the device's own width so it is not upscaled on tall screens and
/// not wastefully large on small ones.
class LaunchPoster {
  LaunchPoster._();

  static const _asset = 'assets/launch/launch_poster.jpg';

  static ui.Image? _image;
  static Future<ui.Image?>? _pending;

  /// The decoded poster, or null while loading / when it cannot be read.
  static ui.Image? get image => _image;

  /// Decodes the poster if it is not decoded yet. Safe to call repeatedly.
  static Future<ui.Image?> load(BuildContext context) {
    if (_image != null) return Future.value(_image);
    return _pending ??= _decode(context);
  }

  static Future<ui.Image?> _decode(BuildContext context) async {
    try {
      final dpr = MediaQuery.maybeDevicePixelRatioOf(context) ?? 1.0;
      final width = (MediaQuery.maybeSizeOf(context)?.width ?? 400) * dpr;
      // Never decode wider than the source, and keep it reasonable.
      final target = width.clamp(320.0, 1152.0);

      final data = await rootBundle.load(_asset);
      final codec = await ui.instantiateImageCodec(
        data.buffer.asUint8List(),
        targetWidth: target.round(),
      );
      final frame = await codec.getNextFrame();
      _image = frame.image;
      return _image;
    } catch (_) {
      // A missing or damaged asset must not break the first run: the page
      // falls back to its normal gradient.
      return null;
    } finally {
      _pending = null;
    }
  }
}

/// Paints the poster full-bleed behind [child], with a scrim so text on top
/// stays readable.
///
/// The poster is a tall portrait composition. [BoxFit.cover] fills any aspect
/// ratio without letterboxing; the artwork is centred, so cropping the long
/// edges keeps the composition intact.
class LaunchPosterBackdrop extends StatelessWidget {
  const LaunchPosterBackdrop({super.key, required this.child});

  final Widget child;

  /// How strongly the poster is dimmed under the page content. The welcome page
  /// draws light text over it, so it needs to sit back.
  static const scrim = 0.28;

  @override
  Widget build(BuildContext context) {
    final image = LaunchPoster.image;
    if (image == null) {
      // Not decoded yet (or unavailable): plain surface, no flash of a wrong
      // gradient. _PosterLoader above retries and rebuilds.
      return ColoredBox(color: const Color(0xFF111115), child: child);
    }
    return Stack(
      fit: StackFit.expand,
      children: [
        Positioned.fill(
          child: IgnorePointer(
            child: RepaintBoundary(
              child: RawImage(
                image: image,
                fit: BoxFit.cover,
                alignment: Alignment.center,
                filterQuality: FilterQuality.medium,
              ),
            ),
          ),
        ),
        // A gentle scrim: keeps the artwork visible while giving the copy
        // enough contrast on both light and dark builds.
        Positioned.fill(
          child: IgnorePointer(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.black.withValues(alpha: scrim),
                    Colors.black.withValues(alpha: scrim * 0.6),
                    Colors.black.withValues(alpha: scrim),
                  ],
                  stops: const [0.0, 0.45, 1.0],
                ),
              ),
            ),
          ),
        ),
        child,
      ],
    );
  }
}

/// Loads the poster on first build and rebuilds once it is ready.
class LaunchPosterLoader extends StatefulWidget {
  const LaunchPosterLoader({super.key, required this.builder});

  final WidgetBuilder builder;

  @override
  State<LaunchPosterLoader> createState() => _LaunchPosterLoaderState();
}

class _LaunchPosterLoaderState extends State<LaunchPosterLoader> {
  @override
  void initState() {
    super.initState();
    if (LaunchPoster.image == null) {
      LaunchPoster.load(context).then((image) {
        if (mounted && image != null) setState(() {});
      });
    }
  }

  @override
  Widget build(BuildContext context) => widget.builder(context);
}
