#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 WhaleTail（鲸鱼尾巴精灵图）换成无限符号绘制
=============================================

WhaleTail 用在两处：
  ui/chat/empty_state.dart          空状态「夜深了」上方的插图
  ui/chat/widgets/activity_strip.dart  活动条的进度指示

它是 dsh-go 的品牌素材（assets/whale/ 的精灵图）。这里保留类名与构造参数
（level / color / height / still），只把内部的精灵图绘制换成无限符号，
调用方一行都不用改。

无限符号用 Path 画：两层椭圆环 + evenOdd 挖空，按高度自适应宽度。
仍保留「按 level 变化亮度」的语义，让活动条还能表达忙闲。
"""

from __future__ import annotations

import os
import re

P = r"D:\dsh-go\replica\app\lib\ui\chat\widgets\whale_tail.dart"

NEW_IMPL = '''// The activity indicator: an infinity mark that "breathes" with the run's speed.
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
  void didUpdateWidget(WhaleTail old) {
    super.didUpdateWidget(old);
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
'''

raw = open(P, encoding="utf-8", newline="").read()
open(P, "w", encoding="utf-8", newline="").write(NEW_IMPL)
print(f"已替换 whale_tail.dart（原 {len(raw)} 字符 -> 新 {len(NEW_IMPL)} 字符）")
print("  保留的公开接口: WhaleTail(level, color, height, still) / WhaleTailState")
