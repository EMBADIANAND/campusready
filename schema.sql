-- ============================================
-- CampusReady Database Schema
-- Run this file once to set up your database
-- ============================================

-- Create the database
CREATE DATABASE IF NOT EXISTS campusready;
USE campusready;

-- ─────────────────────────────────────────────
-- STUDENTS TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)   NOT NULL,
    email         VARCHAR(150)   NOT NULL UNIQUE,
    password      VARCHAR(255)   NOT NULL,        -- bcrypt hashed
    college       VARCHAR(200)   NOT NULL,
    branch        VARCHAR(50)    NOT NULL,
    year          VARCHAR(20)    NOT NULL,
    cgpa          DECIMAL(3,1)   NOT NULL,

    -- Quiz scores (updated after each quiz)
    aptitude_score      INT DEFAULT 0,
    reasoning_score     INT DEFAULT 0,
    coding_score        INT DEFAULT 0,
    communication_score INT DEFAULT 0,
    readiness_score     INT DEFAULT 0,
    quizzes_taken       INT DEFAULT 0,

    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- COMPANIES TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS companies (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    company_name   VARCHAR(150)  NOT NULL,
    industry       VARCHAR(100)  NOT NULL,
    email          VARCHAR(150)  NOT NULL UNIQUE,
    password       VARCHAR(255)  NOT NULL,         -- bcrypt hashed
    contact_person VARCHAR(100)  NOT NULL,
    phone          VARCHAR(20)   NOT NULL,
    website        VARCHAR(200),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- QUIZ QUESTIONS TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_questions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    topic          ENUM('aptitude','reasoning','coding','communication') NOT NULL,
    question       TEXT          NOT NULL,
    option1        VARCHAR(255)  NOT NULL,
    option2        VARCHAR(255)  NOT NULL,
    option3        VARCHAR(255)  NOT NULL,
    option4        VARCHAR(255)  NOT NULL,
    correct_answer INT           NOT NULL,   -- 0,1,2,3 (index of correct option)
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- QUIZ RESULTS TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_results (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT          NOT NULL,
    topic       VARCHAR(50)  NOT NULL,
    score       INT          NOT NULL,   -- percentage 0-100
    taken_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- SHORTLISTS TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shortlists (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    company_id  INT NOT NULL,
    student_id  INT NOT NULL,
    shortlisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id)  ON DELETE CASCADE,
    UNIQUE KEY unique_shortlist (company_id, student_id)  -- prevent duplicates
);

-- ─────────────────────────────────────────────
-- SEED: Default Quiz Questions (Aptitude)
-- ─────────────────────────────────────────────
INSERT INTO quiz_questions (topic, question, option1, option2, option3, option4, correct_answer) VALUES
('aptitude', 'If a train travels 60 km in 1 hour, how far will it travel in 2.5 hours?', '120 km', '150 km', '180 km', '90 km', 1),
('aptitude', 'What is 15% of 200?', '25', '30', '35', '20', 1),
('aptitude', 'A shopkeeper sells an item for Rs.120 at 20% profit. What is the cost price?', 'Rs.90', 'Rs.96', 'Rs.100', 'Rs.110', 2),
('aptitude', 'If 6 workers complete a job in 8 days, how many days will 4 workers take?', '10 days', '12 days', '14 days', '16 days', 1),
('aptitude', 'What comes next: 2, 4, 8, 16, ?', '24', '28', '32', '36', 2),

-- Reasoning
('reasoning', 'Which number is the odd one out: 2, 3, 5, 7, 9, 11?', '2', '9', '11', '3', 1),
('reasoning', 'If APPLE = ELPPA, then MANGO = ?', 'OGNAM', 'OGNMA', 'OGAMN', 'OGANM', 0),
('reasoning', 'A is B''s brother. B is C''s sister. What is A to C?', 'Sister', 'Brother', 'Father', 'Cannot determine', 1),
('reasoning', 'Complete the pattern: 1, 4, 9, 16, 25, ?', '30', '36', '42', '49', 1),
('reasoning', 'If CAT = 3120, then DOG = ?', '4157', '4156', '4158', '4155', 0),

-- Coding
('coding', 'What does HTML stand for?', 'Hyper Text Markup Language', 'High Text Machine Language', 'Hyper Transfer Markup Language', 'None', 0),
('coding', 'Which CSS property changes text color?', 'font-color', 'text-color', 'color', 'background-color', 2),
('coding', 'What does CSS stand for?', 'Computer Style Sheets', 'Cascading Style Sheets', 'Creative Style Sheets', 'Colorful Style Sheets', 1),
('coding', 'Which tag creates a hyperlink in HTML?', '<link>', '<a>', '<href>', '<url>', 1),
('coding', 'What does display: flex do in CSS?', 'Hides the element', 'Makes element flexible/side by side', 'Changes font size', 'Adds border', 1),

-- Communication
('communication', 'Which of these is the most professional email greeting?', 'Hey!', 'Yo!', 'Dear Sir/Madam,', 'Wassup,', 2),
('communication', 'Active listening means:', 'Talking more than listening', 'Fully concentrating on the speaker', 'Checking phone while listening', 'Interrupting frequently', 1),
('communication', 'In a group discussion, you should:', 'Dominate the conversation', 'Stay completely silent', 'Contribute meaningfully and listen to others', 'Argue with everyone', 2),
('communication', 'Body language accounts for what percentage of communication?', '10%', '30%', '55%', '90%', 2),
('communication', 'The best way to handle a question you don''t know in an interview:', 'Make up an answer', 'Say I don''t know honestly and offer to find out', 'Change the topic', 'Stay silent', 1);
