// The activity indicator: an infinity mark that "breathes" with the run's speed.
//
// This used to be a whale-tail sprite sheet (assets/whale/). The whale was
// dsh-go brand art, so this build draws a neutral mark instead: the same
// infinity glyph as the app icon, painted with a Path so it scales cleanly and
// needs no assets.
//
// The public surface is unchanged (WhaleTail / level / color / height / still),
// so every call site keeps working: the composer's activity strip and the empty
// state's illustration.

import 'dart:math' as math;

import 'package:flutter/scheduler.dart';
import 'package:flutter/widgets.dart';

/// The brand blue for the mark on light surfaces.
const deepSeekBlue = Color(0xFF4D6BFE);

/// The same hue on dark surfaces (4.2:1 on #14171E..#343944).
const deepSeekBlueDark = Color(0xFF7A98FB);

/// The mark's tint for a theme brightness.
Color whaleColorFor(Brightness brightness) =>
    brightness == Brightness.dark ? deepSeekBlueDark : deepSeekBlue;

/// The brand mark, one flat tint (a busy indicator is not a place for gradients).
class WhaleTail extends StatefulWidget {
  const WhaleTail({super.key, this.level = 1, required this.color, this.height = 20, this.still = false});

  /// 0 = waiting, 1..4 = increasingly busy. Drives how fast the mark pulses.
  final int level;

  final Color color;

  /// Height of the mark; width follows the glyph's 1.09 aspect.
  final double height;

  /// No animation (reduced motion, or a still illustration).
  final bool still;

  @override
  State<WhaleTail> createState() => WhaleTailState();
}

class WhaleTailState extends State<WhaleTail> with SingleTickerProviderStateMixin {
  late final Ticker _ticker = createTicker(_onTick);
  final _repaint = ValueNotifier<int>(0);

  double _rate = 0;
  double _phase = 0;
  Duration _last = Duration.zero;

  static const _aspect = 1.09;

  static double rateOf(int level) => switch (level) {
    <= 0 => 0.25,
    1 => 0.45,
    _ => 0.9,
  };

  @override
  void initState() {
    super.initState();
    _rate = rateOf(widget.level);
    if (!widget.still) _ticker.start();
  }

  @override
  void didUpdateWidget(WhaleTail oldWidget) {
    super.didUpdateWidget(oldWidget);
    _rate = rateOf(widget.level);
    if (widget.still && _ticker.isActive) {
      _ticker.stop();
    } else if (!widget.still && !_ticker.isActive) {
      _ticker.start();
    }
  }

  void _onTick(Duration elapsed) {
    final dt = (elapsed - _last).inMicroseconds / 1e6;
    _last = elapsed;
    _phase = (_phase + dt * _rate) % 1.0;
    _repaint.value++;
  }

  @override
  void dispose() {
    _ticker.dispose();
    _repaint.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(
        size: Size(widget.height * _aspect, widget.height),
        painter: _InfinityPainter(
          color: widget.color,
          phase: widget.still ? 0 : _phase,
          repaint: _repaint,
        ),
      ),
    );
  }
}

/// Draws the infinity mark as a stroked band, breathing with [phase].
class _InfinityPainter extends CustomPainter {
  _InfinityPainter({required this.color, required this.phase, required this.repaint})
    : super(repaint: repaint);

  final Color color;
  final double phase;
  final ValueNotifier<int> repaint;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final cx = w / 2;
    final cy = h / 2;

    // A gentle pulse: the ink thickens and fades a little as the run works.
    final pulse = 0.5 + 0.5 * math.sin(phase * 2 * math.pi);
    final stroke = h * (0.16 + 0.04 * pulse);
    final alpha = 0.62 + 0.38 * pulse;

    final halfW = w * 0.42;
    final halfH = h * 0.30;

    final path = Path()
      ..moveTo(cx - halfW, cy)
      // left lobe, upper arc into the crossing
      ..cubicTo(cx - halfW, cy - halfH, cx - halfW * 0.42, cy - halfH, cx, cy)
      // crossing out to the right lobe
      ..cubicTo(cx + halfW * 0.42, cy - halfH, cx + halfW, cy - halfH, cx + halfW, cy)
      // right lobe, back through the crossing
      ..cubicTo(cx + halfW, cy + halfH, cx + halfW * 0.42, cy + halfH, cx, cy)
      // and home through the left lobe
      ..cubicTo(cx - halfW * 0.42, cy + halfH, cx - halfW, cy + halfH, cx - halfW, cy);

    canvas.drawPath(
      path,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..color = color.withValues(alpha: color.a * alpha)
        ..isAntiAlias = true,
    );
  }

  @override
  bool shouldRepaint(_InfinityPainter old) => old.color != color || old.phase != phase;
}
