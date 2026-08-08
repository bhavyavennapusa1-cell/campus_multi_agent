import React from "react";
import { HowItWorks } from "@/components/ui/how-it-works";

const organizeSteps = [
  {
    title: "Compile Syllabi & Resources",
    description: "Automatically gather all course materials, syllabus PDFs, and lab manuals in one place.",
    colorTheme: "blue"
  },
  {
    title: "Analyze Current Standing",
    description: "Cross-reference your attendance metrics and past grades to identify high-priority subjects.",
    colorTheme: "orange"
  },
  {
    title: "Generate Study Plan",
    description: "Let the AI Orchestrator create a day-by-day timetable leading up to your midterm exams.",
    colorTheme: "purple"
  },
  {
    title: "Execute & Track",
    description: "Follow the daily roadmap and sync completed tasks with your calendar.",
    colorTheme: "blue"
  }
];

export default function OrganizePage() {
  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Smart Campus AI | Study Organizer
          </h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Automated Subject-Specific Roadmap & Exam Preparation Engine
          </p>
        </header>

        <HowItWorks features={organizeSteps} />
      </div>
    </main>
  );
}
