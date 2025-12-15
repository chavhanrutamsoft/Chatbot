<?php
/**
 * API endpoint for the QuotePlan Chatbot
 * Receives questions and returns answers from the RAG system
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(400);
    echo json_encode(['error' => 'Only POST requests are allowed']);
    exit();
}

// Get the question from POST data
$input = json_decode(file_get_contents('php://input'), true);
$question = $input['question'] ?? '';

if (empty($question)) {
    http_response_code(400);
    echo json_encode(['error' => 'Question is required']);
    exit();
}

// Sanitize the question
$question = escapeshellarg($question);

// Call the Python query bot
$python_cmd = "python query_bot.py --q {$question} 2>&1";
$output = shell_exec($python_cmd);

if ($output === null) {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to execute query bot']);
    exit();
}

// Parse the output to extract the answer
// The output format is:
// Loading local embedding model...
// ❓ Question: ...
// 🔍 Embedding question...
// 📚 Searching Qdrant...
// 💬 Calling chat API...
// ✅ Answer:
// [Answer text here]

$lines = explode("\n", $output);
$answer_started = false;
$answer = '';

foreach ($lines as $line) {
    if (strpos($line, '✅ Answer:') !== false) {
        $answer_started = true;
        continue;
    }
    
    if ($answer_started && !empty(trim($line))) {
        $answer .= trim($line) . "\n";
    }
}

$answer = trim($answer);

if (empty($answer)) {
    // If we couldn't parse the answer in the expected format, return the full output
    $answer = trim($output);
}

echo json_encode([
    'success' => true,
    'question' => $input['question'],
    'answer' => $answer
]);
?>
