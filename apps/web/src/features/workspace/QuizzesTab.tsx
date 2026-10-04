import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, HelpCircle, Loader2, Plus, RefreshCw, RotateCcw, XCircle } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";
import { useAuth } from "../auth/AuthContext";
import {
  generateQuiz,
  listQuizzes,
  submitQuizAttempt,
  type QuizAttemptResult,
  type QuizPublic,
} from "../../lib/api-client";
import type { Project } from "../../types";

interface QuizzesTabProps {
  project: Project;
}

export function QuizzesTab({ project }: QuizzesTabProps) {
  const { token } = useAuth();
  const [quizzes, setQuizzes] = useState<QuizPublic[]>([]);
  const [activeQuiz, setActiveQuiz] = useState<QuizPublic | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [attemptResult, setAttemptResult] = useState<QuizAttemptResult | null>(null);

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState(`${project.name} Practice Exam`);
  const [topic, setTopic] = useState("");
  const [numQuestions, setNumQuestions] = useState(3);
  const [difficulty, setDifficulty] = useState<string>("medium");
  const [isGenerating, setIsGenerating] = useState(false);

  const fetchQuizzes = useCallback(async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      setError(null);
      const res = await listQuizzes(token, project.id);
      setQuizzes(res.quizzes);
      if (res.quizzes.length > 0) {
        setActiveQuiz(res.quizzes[0]);
      } else {
        setActiveQuiz(null);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load quizzes");
    } finally {
      setIsLoading(false);
    }
  }, [token, project.id]);

  useEffect(() => {
    fetchQuizzes();
  }, [fetchQuizzes]);

  const handleSelectOption = (questionId: string, option: string) => {
    if (attemptResult) return;
    setUserAnswers((prev) => ({ ...prev, [questionId]: option }));
  };

  const handleReset = () => {
    setUserAnswers({});
    setAttemptResult(null);
  };

  const handleSubmitAttempt = async () => {
    if (!token || !activeQuiz) return;
    const formattedAnswers = Object.entries(userAnswers).map(([qid, ans]) => ({
      question_id: qid,
      submitted_answer: ans,
    }));
    if (formattedAnswers.length === 0) return;

    try {
      setIsSubmitting(true);
      setError(null);
      const result = await submitQuizAttempt(token, project.id, activeQuiz.id, formattedAnswers);
      setAttemptResult(result);
    } catch (err: any) {
      setError(err?.message || "Failed to submit quiz attempt");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    try {
      setIsGenerating(true);
      setError(null);
      const newQuiz = await generateQuiz(token, project.id, {
        title: title.trim() || undefined,
        topic: topic.trim() || undefined,
        num_questions: numQuestions,
        difficulty,
      });
      setQuizzes((prev) => [newQuiz, ...prev]);
      setActiveQuiz(newQuiz);
      setUserAnswers({});
      setAttemptResult(null);
      setShowCreateModal(false);
    } catch (err: any) {
      setError(err?.message || "Failed to generate quiz");
    } finally {
      setIsGenerating(false);
    }
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
            Test retention with source-grounded quizzes. Answers are strictly protected until submission.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => fetchQuizzes()}
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />}
          >
            Refresh
          </Button>
          <Button
            onClick={() => setShowCreateModal(true)}
            size="sm"
            leftIcon={<Plus className="w-3.5 h-3.5" />}
          >
            Create New Quiz
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 text-xs bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Quiz selector tabs if multiple */}
      {quizzes.length > 1 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-slate-200 text-xs">
          {quizzes.map((q) => (
            <button
              key={q.id}
              onClick={() => {
                setActiveQuiz(q);
                setUserAnswers({});
                setAttemptResult(null);
              }}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap ${
                activeQuiz?.id === q.id
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {q.title}
            </button>
          ))}
        </div>
      )}

      {isLoading && quizzes.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
          <span>Loading practice quizzes...</span>
        </div>
      ) : activeQuiz ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">
                Active Assessment
              </span>
              <h3 className="text-sm font-bold text-slate-900 mt-0.5">{activeQuiz.title}</h3>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="indigo">
                {attemptResult ? "Attempt Evaluated" : "Protected Answers"}
              </Badge>
              {attemptResult && (
                <Badge variant={attemptResult.percentage >= 70 ? "emerald" : "amber"}>
                  Score: {attemptResult.correct_count} / {attemptResult.total_questions} ({attemptResult.percentage.toFixed(0)}%)
                </Badge>
              )}
            </div>
          </div>

          {/* Question List */}
          <div className="space-y-6">
            {activeQuiz.questions.map((q) => {
              const selected = userAnswers[q.id];
              const qResult = attemptResult?.results.find((r) => r.question_id === q.id);

              return (
                <div key={q.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-3">
                  <div className="flex items-start justify-between">
                    <span className="font-bold text-slate-900">
                      Question {q.position}: {q.prompt}
                    </span>
                    <Badge variant="slate">{q.difficulty}</Badge>
                  </div>

                  {/* Options if MCQ */}
                  {q.options && q.options.length > 0 ? (
                    <div className="space-y-2 pt-1">
                      {q.options.map((opt) => {
                        const isOptionSelected = selected === opt;
                        let optionClasses =
                          "p-2.5 rounded-lg border text-xs text-left w-full transition-colors flex items-center justify-between ";

                        if (!attemptResult) {
                          optionClasses += isOptionSelected
                            ? "bg-indigo-50 border-indigo-500 text-indigo-900 font-semibold"
                            : "bg-white border-slate-200 text-slate-700 hover:bg-slate-100";
                        } else {
                          if (opt === qResult?.expected_answer) {
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
                            onClick={() => handleSelectOption(q.id, opt)}
                            disabled={!!attemptResult}
                            className={optionClasses}
                          >
                            <span>{opt}</span>
                            {attemptResult && opt === qResult?.expected_answer && (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 ml-2" />
                            )}
                            {attemptResult && isOptionSelected && opt !== qResult?.expected_answer && (
                              <XCircle className="w-4 h-4 text-red-600 shrink-0 ml-2" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    /* Free text answer input */
                    <div className="pt-1">
                      <input
                        type="text"
                        disabled={!!attemptResult}
                        value={selected || ""}
                        onChange={(e) => handleSelectOption(q.id, e.target.value)}
                        placeholder="Type your answer here..."
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white"
                      />
                    </div>
                  )}

                  {/* Revealed Explanation upon submission */}
                  {qResult && (
                    <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200 text-[11px] text-slate-600 space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-800">Status:</span>
                        <span className={qResult.is_correct ? "text-emerald-700 font-semibold" : "text-red-700 font-semibold"}>
                          {qResult.is_correct ? "Correct" : "Incorrect"}
                        </span>
                      </div>
                      <div>
                        <span className="font-bold text-slate-800">Expected: </span>
                        <span>{qResult.expected_answer}</span>
                      </div>
                      <div>
                        <span className="font-bold text-slate-800">Explanation: </span>
                        <span>{qResult.explanation}</span>
                      </div>
                      {qResult.source_citations && qResult.source_citations.length > 0 && (
                        <div className="text-[10px] text-indigo-700 pt-1">
                          Source citation: Chunk {qResult.source_citations[0].chunk_id || "Document Reference"}
                        </div>
                      )}
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
            {!attemptResult ? (
              <Button
                size="sm"
                onClick={handleSubmitAttempt}
                disabled={isSubmitting || Object.keys(userAnswers).length === 0}
                leftIcon={isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : undefined}
              >
                {isSubmitting ? "Grading..." : "Submit Attempt & Reveal Explanations"}
              </Button>
            ) : (
              <span className="text-xs text-slate-500 font-medium">Attempt submitted & scored</span>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500">
          No quizzes generated for this project yet. Click &quot;Create New Quiz&quot; above to generate one from your documents.
        </div>
      )}

      {/* Create Quiz Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Generate Practice Quiz"
        description="Configure target question count and focus topics from your course materials."
      >
        <form onSubmit={handleCreateQuiz} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Assessment Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Topic / Concept Focus (Optional)
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Master Theorem or RRF Hybrid Retrieval"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Question Count
              </label>
              <select
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white"
              >
                <option value={3}>3 Questions</option>
                <option value={5}>5 Questions</option>
                <option value={10}>10 Questions</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Difficulty Level
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white"
              >
                <option value="easy">Introductory</option>
                <option value="medium">Medium</option>
                <option value="hard">Comprehensive</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isGenerating}
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isGenerating}
              leftIcon={isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : undefined}
            >
              {isGenerating ? "Generating..." : "Create Quiz"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

