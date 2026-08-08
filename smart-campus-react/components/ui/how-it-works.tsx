"use client";

import React from "react";
import { LazyMotion, domAnimation, m } from "framer-motion";
import { BookOpen, BarChart3, Calendar, CheckCircle2, ArrowRight } from "lucide-react";

export interface FeatureStep {
  title: string;
  description: string;
  colorTheme?: "blue" | "orange" | "purple" | string;
}

interface HowItWorksProps {
  features: FeatureStep[];
}

const themeStyles = {
  blue: {
    bg: "bg-blue-50 dark:bg-blue-950/30",
    border: "border-blue-300 dark:border-blue-800",
    text: "text-blue-600 dark:text-blue-400",
    badge: "bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300",
    pin: "#3b82f6",
    icon: BookOpen,
  },
  orange: {
    bg: "bg-amber-50 dark:bg-amber-950/30",
    border: "border-amber-300 dark:border-amber-800",
    text: "text-amber-600 dark:text-amber-400",
    badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300",
    pin: "#f59e0b",
    icon: BarChart3,
  },
  purple: {
    bg: "bg-purple-50 dark:bg-purple-950/30",
    border: "border-purple-300 dark:border-purple-800",
    text: "text-purple-600 dark:text-purple-400",
    badge: "bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-300",
    pin: "#8b5cf6",
    icon: Calendar,
  },
};

export function HowItWorks({ features }: HowItWorksProps) {
  return (
    <LazyMotion features={domAnimation}>
      <div className="w-full max-w-5xl mx-auto py-12 px-4 sm:px-6">
        <div className="text-center mb-12">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 mb-3">
            <CheckCircle2 className="w-3.5 h-3.5" /> AI Academic Roadmap
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            How Organize Study Engine Works
          </h2>
          <p className="mt-2 text-base text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
            From raw syllabi to automated daily tasks — structured preparation tailored to your target exam deadline.
          </p>
        </div>

        <div className="relative">
          {/* SVG Animated Connecting Path */}
          <svg
            className="absolute left-6 top-10 bottom-10 w-1 hidden md:block overflow-visible"
            viewBox="0 0 2 600"
            fill="none"
          >
            <m.path
              d="M 1 0 V 600"
              stroke="url(#gradient-line)"
              strokeWidth="3"
              strokeDasharray="8 8"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              transition={{ duration: 1.5, ease: "easeInOut" }}
            />
            <defs>
              <linearGradient id="gradient-line" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="50%" stopColor="#f59e0b" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
          </svg>

          {/* Timeline Feature Steps */}
          <div className="space-y-8 relative">
            {features.map((step, idx) => {
              const themeKey = (step.colorTheme as keyof typeof themeStyles) || "blue";
              const style = themeStyles[themeKey] || themeStyles.blue;
              const IconComponent = style.icon;

              return (
                <m.div
                  key={idx}
                  initial={{ opacity: 0, y: 25 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: idx * 0.15 }}
                  viewport={{ once: true }}
                  className="flex flex-col md:flex-row items-start gap-6 group"
                >
                  {/* Step Badge Node */}
                  <div className="flex items-center gap-3 shrink-0">
                    <div
                      className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-lg border ${style.bg} ${style.border} ${style.text} shadow-md group-hover:scale-110 transition-transform duration-300`}
                    >
                      {idx + 1}
                    </div>
                    <div className="h-0.5 w-6 bg-slate-300 dark:bg-slate-700 hidden md:block" />
                  </div>

                  {/* Feature Content Card */}
                  <div
                    className={`flex-1 rounded-2xl p-6 border ${style.bg} ${style.border} shadow-sm group-hover:shadow-lg transition-all duration-300 relative overflow-hidden`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <IconComponent className={`w-5 h-5 ${style.text}`} />
                        <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                          {step.title}
                        </h3>
                      </div>
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${style.badge}`}>
                        Phase {idx + 1}
                      </span>
                    </div>

                    <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
                      {step.description}
                    </p>

                    <div className="mt-4 flex items-center text-xs font-semibold text-slate-500 group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors">
                      <span>Explore workflow details</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </m.div>
              );
            })}
          </div>
        </div>
      </div>
    </LazyMotion>
  );
}
