import { useState } from "react";
import { CheckCircle2, HelpCircle, Plus, RotateCcw, XCircle } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import type { Project, Quiz, QuizQuestion } from "../../types";

interface QuizzesTabProps {
  project: Project;
}

export function QuizzesTab({ project }: QuizzesTabProps) {
  const [quizzes] = useState<Quiz[]>([
    {
      id: "quiz-1",
      project_id: project.id,
      workspace_id: project.workspace_id,
      title: "Midterm Preparation — Core Concepts",
      question_count: 2,
      status: "ready",
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
  ]);

  const [activeQuiz] = useState<Quiz | null>(quizzes[0]);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Sample questions demonstrating protected answer keys
  const sampleQuestions: QuizQuestion[] = [
    {
      id: "q-1",
      quiz_id: "quiz-1",
      question_type: "multiple_choice",
      difficulty: "medium",
      prompt: "In hybrid retrieval architectures, what is the role of Reciprocal Rank Fusion (RRF)?",
      options: [
        "To combine dense semantic vectors and lexical sparse keyword result ranks without score calibration",
        "To encrypt database passwords before sending queries to pgvector",
        "To convert scanned PDF documents directly into vector embeddings",
        "To bypass Row-Level Security during background worker indexing",
      ],
      expected_answer:
        "To combine dense semantic vectors and lexical sparse keyword result ranks without score calibration",
      explanation:
        "Section 7.1 of the Master Architecture specifies RRF to merge vector and lexical candidate lists by ranking position rather than raw similarity scores.",
      position: 1,
    },
    {
      id: "q-2",
      quiz_id: "quiz-1",
      question_type: "multiple_choice",
      difficulty: "easy",
      prompt: "Why does StudySpace AI enforce tenant isolation at the PostgreSQL database level?",
      options: [
        "To prevent cross-tenant exposure and ensure students never retrieve another user's documents",
        "To increase the speed of client-side animation rendering",
        "To eliminate the need for embedding models",
        "To share private course notes across all university students",
      ],
      expected_answer:
        "To prevent cross-tenant exposure and ensure students never retrieve another user's documents",
      explanation:
        "Principle 2 of Master Architecture Section 1.3 mandates that users must never retrieve another user's documents, chunks, chats, or cached answers.",
      position: 2,
    },
  ];

  const handleSelectOption = (qPos: number, option: string) => {
    if (submitted) return;
    setUserAnswers({ ...userAnswers, [qPos]: option });
  };

  const calculateScore = () => {
    let score = 0;
    sampleQuestions.forEach((q) => {
      if (userAnswers[q.position] === q.expected_answer) {
        score++;
      }
    });
    return score;
  };

  const handleReset = () => {
    setUserAnswers({});
    setSubmitted(false);
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <HelpCircle className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Source-Grounded Practice Quizzes
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Test retention with AI-generated quizzes bound to verified course materials.
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          size="sm"
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          Create New Quiz
        </Button>
      </div>

      {/* Active Quiz Card */}
      {activeQuiz ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">
                Active Assessment
              </span>
              <h3 className="text-sm font-bold text-slate-900 mt-0.5">{activeQuiz.title}</h3>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="indigo">Protected Answers</Badge>
              {submitted && (
                <Badge variant="emerald">
                  Score: {calculateScore()} / {sampleQuestions.length}
                </Badge>
              )}
            </div>
          </div>

          {/* Question List */}
          <div className="space-y-6">
            {sampleQuestions.map((q) => {
              const selected = userAnswers[q.position];

              return (
                <div key={q.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-3">
                  <div className="flex items-start justify-between">
                    <span className="font-bold text-slate-900">
                      Question {q.position}: {q.prompt}
                    </span>
                    <Badge variant="slate">{q.difficulty}</Badge>
                  </div>

                  {/* Options */}
                  <div className="space-y-2 pt-1">
                    {q.options?.map((opt) => {
                      const isOptionSelected = selected === opt;
                      let optionClasses =
                        "p-2.5 rounded-lg border text-xs text-left w-full transition-colors flex items-center justify-between ";

                      if (!submitted) {
                        optionClasses += isOptionSelected
                          ? "bg-indigo-50 border-indigo-500 text-indigo-900 font-semibold"
                          : "bg-white border-slate-200 text-slate-700 hover:bg-slate-100";
                      } else {
                        if (opt === q.expected_answer) {
                          optionClasses += "bg-emerald-50 border-emerald-400 text-emerald-900 font-semibold";
                        } else if (isOptionSelected) {
                          optionClasses += "bg-red-50 border-red-300 text-red-900";
                        } else {
                          optionClasses += "bg-white border-slate-200 text-slate-400";
                        }
                      }

                      return (
                        <button
                          key={opt}
                          onClick={() => handleSelectOption(q.position, opt)}
                          disabled={submitted}
                          className={optionClasses}
                        >
                          <span>{opt}</span>
                          {submitted && opt === q.expected_answer && (
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 ml-2" />
                          )}
                          {submitted && isOptionSelected && opt !== q.expected_answer && (
                            <XCircle className="w-4 h-4 text-red-600 shrink-0 ml-2" />
                          )}
                        </button>
                      );
                    })}
                  </div>

                  {/* Protected Explanation revealed strictly upon submission */}
                  {submitted && (
                    <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200 text-[11px] text-slate-600 space-y-1">
                      <span className="font-bold text-slate-800 block">Explanation & Syllabus Citation:</span>
                      <p>{q.explanation}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              Reset Attempt
            </Button>
            {!submitted ? (
              <Button
                size="sm"
                onClick={() => setSubmitted(true)}
                disabled={Object.keys(userAnswers).length === 0}
              >
                Submit Attempt & Reveal Explanations
              </Button>
            ) : (
              <span className="text-xs text-slate-500 font-medium">Attempt submitted & scored</span>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500">
          No quizzes generated for this project yet.
        </div>
      )}

      {/* Create Quiz Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Generate Practice Quiz"
        description="Configure target question count and focus topics."
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Assessment Title *
            </label>
            <input
              type="text"
              defaultValue={`${project.name} Practice Exam`}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Question Count
              </label>
              <select className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white">
                <option value="5">5 Questions</option>
                <option value="10">10 Questions</option>
                <option value="15">15 Questions</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Difficulty Level
              </label>
              <select className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white">
                <option value="medium">Medium</option>
                <option value="easy">Introductory</option>
                <option value="hard">Comprehensive</option>
              </select>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-500 text-[11px]">
            Quiz generation automatically scopes to indexed project files. Real model generation activates in Phase 6.
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => setShowCreateModal(false)}>
              Create Quiz
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
